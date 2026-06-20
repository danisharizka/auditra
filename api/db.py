"""DuckDB data layer — materialized cache for fast repeated queries."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import duckdb
import pandas as pd

from api.cache import TTLCache
from api.config import (
    DASHBOARD_CACHE_SIZE,
    DATA_NETWORK_CSV,
    DATA_NETWORK_PARQUET,
    DUCKDB_CACHE,
    GEO_LOOKUP_CSV,
    GEOJSON_PATH,
    KG_EDGES_CSV,
    KG_NODES_CSV,
)
from api.filters import build_where


class DataStore:
    """Singleton DuckDB over a materialized local cache (auditra.duckdb)."""

    _instance: "DataStore | None" = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dashboard_cache = TTLCache(maxsize=DASHBOARD_CACHE_SIZE, ttl_seconds=600)
        self._packages_cache = TTLCache(maxsize=128, ttl_seconds=120)
        self._filter_options_cache: dict | None = None
        self._meta_cache: dict | None = None
        self._geojson_cache: dict | None = None
        self._kg_nodes: pd.DataFrame | None = None
        self._kg_edges: pd.DataFrame | None = None
        self.source_path = ""
        self.source_kind = ""

        t0 = time.perf_counter()
        self._ensure_database()
        self.conn = duckdb.connect(str(DUCKDB_CACHE), read_only=False)
        self._configure_session()
        self._warm_static_caches()
        elapsed = time.perf_counter() - t0
        print(f"[Auditra] Database ready in {elapsed:.1f}s ({self._meta_cache['total_rows']:,} rows)")

    @classmethod
    def get(cls) -> "DataStore":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_session(self) -> None:
        threads = min(8, max(2, __import__("os").cpu_count() or 4))
        self.conn.execute(f"SET threads TO {threads}")
        self.conn.execute("SET enable_object_cache TO true")

    def _source_mtime(self) -> float:
        if DATA_NETWORK_PARQUET.exists():
            return DATA_NETWORK_PARQUET.stat().st_mtime
        return DATA_NETWORK_CSV.stat().st_mtime

    def _cache_is_fresh(self) -> bool:
        if not DUCKDB_CACHE.exists():
            return False
        try:
            return DUCKDB_CACHE.stat().st_mtime >= self._source_mtime()
        except OSError:
            return False

    def _ensure_parquet(self) -> Path:
        if DATA_NETWORK_PARQUET.exists():
            return DATA_NETWORK_PARQUET
        if not DATA_NETWORK_CSV.exists():
            raise FileNotFoundError(f"Missing {DATA_NETWORK_CSV}")

        print("[Auditra] Converting CSV → Parquet (one-time, ~2-5 min)…")
        t0 = time.perf_counter()
        con = duckdb.connect()
        con.execute(
            f"""
            COPY (
                SELECT * FROM read_csv_auto('{DATA_NETWORK_CSV.as_posix()}', header=true)
            ) TO '{DATA_NETWORK_PARQUET.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        con.close()
        print(f"[Auditra] Parquet saved in {time.perf_counter() - t0:.1f}s")
        return DATA_NETWORK_PARQUET

    def _ensure_database(self) -> None:
        if self._cache_is_fresh():
            self.source_path = str(
                DATA_NETWORK_PARQUET if DATA_NETWORK_PARQUET.exists() else DATA_NETWORK_CSV
            )
            self.source_kind = "duckdb_cache"
            return

        if not DATA_NETWORK_CSV.exists() and not DATA_NETWORK_PARQUET.exists():
            raise FileNotFoundError(
                "Dataset utama belum ada. Jalankan pipeline:\n"
                "  python 01_cleaning.py … python 03b_geo_matching.py"
            )

        parquet = self._ensure_parquet()
        self.source_path = str(parquet)
        self.source_kind = "parquet"

        if DUCKDB_CACHE.exists():
            DUCKDB_CACHE.unlink()

        print("[Auditra] Building DuckDB cache (one-time, ~1-3 min)…")
        t0 = time.perf_counter()
        con = duckdb.connect(str(DUCKDB_CACHE))
        con.execute("SET threads TO 4")

        con.execute(
            f"""
            CREATE TABLE packages AS
            SELECT * FROM read_parquet('{parquet.as_posix()}')
            """
        )

        if GEO_LOOKUP_CSV.exists():
            geo = GEO_LOOKUP_CSV.as_posix()
            con.execute(
                f"""
                CREATE TABLE geo_lookup AS
                SELECT * FROM read_csv_auto('{geo}', header=true)
                """
            )
            con.execute(
                """
                CREATE TABLE packages_geo AS
                SELECT
                    p.id, p.RPI, p.risk_label, p.pagu, p.lembaga, p.metode, p.lokasi,
                    p.s1_metode, p.s2_pagu_anomali, p.s3_fragmentasi, p.s4_konsentrasi,
                    p.s5_umkm, p.s6_dana_metode, p.s7_reputasi, p.paket,
                    g.kabkot_id, g.kabkot_name, g.prov_name
                FROM packages p
                INNER JOIN geo_lookup g ON p.lokasi = g.lokasi_sirup
                """
            )
        else:
            con.execute(
                """
                CREATE TABLE packages_geo AS
                SELECT *, CAST(NULL AS VARCHAR) AS kabkot_id,
                       CAST(NULL AS VARCHAR) AS kabkot_name,
                       CAST(NULL AS VARCHAR) AS prov_name
                FROM packages WHERE 1=0
                """
            )

        con.close()
        print(f"[Auditra] DuckDB cache built in {time.perf_counter() - t0:.1f}s")

    def _warm_static_caches(self) -> None:
        with self._lock:
            row = self.conn.execute("SELECT COUNT(*) FROM packages").fetchone()
            cols = self.conn.execute("DESCRIBE packages").fetchdf()
            self._meta_cache = {
                "total_rows": int(row[0]),
                "total_columns": len(cols),
                "columns": cols["column_name"].tolist(),
                "source_file": str(DUCKDB_CACHE),
                "source_kind": "duckdb_cache",
                "integrity": "full",
                "note": (
                    "Seluruh baris & kolom pipeline tersimpan di server (materialized DuckDB). "
                    "API mengirim agregat/pagination ke browser."
                ),
                "kg_nodes_available": KG_NODES_CSV.exists(),
                "kg_edges_available": KG_EDGES_CSV.exists(),
                "geo_lookup_available": GEO_LOOKUP_CSV.exists(),
            }

        if KG_NODES_CSV.exists():
            self._kg_nodes = pd.read_csv(KG_NODES_CSV)
        if KG_EDGES_CSV.exists():
            self._kg_edges = pd.read_csv(KG_EDGES_CSV)
        if GEOJSON_PATH.exists():
            with open(GEOJSON_PATH, encoding="utf-8") as f:
                self._geojson_cache = json.load(f)

    def meta(self) -> dict:
        return dict(self._meta_cache or {})

    def filter_options(self) -> dict:
        if self._filter_options_cache is not None:
            return self._filter_options_cache

        with self._lock:
            lembaga = self.conn.execute(
                "SELECT DISTINCT lembaga FROM packages "
                "WHERE lembaga IS NOT NULL ORDER BY lembaga"
            ).fetchdf()["lembaga"].tolist()
            metode = self.conn.execute(
                "SELECT DISTINCT metode FROM packages "
                "WHERE metode IS NOT NULL ORDER BY metode"
            ).fetchdf()["metode"].tolist()
            provinsi: list[str] = []
            if GEO_LOOKUP_CSV.exists():
                provinsi = self.conn.execute(
                    "SELECT DISTINCT prov_name FROM geo_lookup ORDER BY prov_name"
                ).fetchdf()["prov_name"].tolist()

        self._filter_options_cache = {
            "lembaga": lembaga,
            "metode": metode,
            "provinsi": provinsi,
        }
        return self._filter_options_cache

    def geojson(self) -> dict:
        if self._geojson_cache is None:
            raise FileNotFoundError(f"Missing {GEOJSON_PATH}")
        return self._geojson_cache

    def _filter_cache_key(
        self,
        provinsi: str,
        lembaga: str,
        metode: str,
        risk_min: float,
        extra: str = "",
    ) -> str:
        return f"{provinsi}|{lembaga}|{metode}|{risk_min}|{extra}"

    def fetch_dashboard_bundle(
        self,
        provinsi: str = "ALL",
        lembaga: str = "ALL",
        metode: str = "ALL",
        risk_min: float = 0,
    ) -> dict:
        key = self._filter_cache_key(provinsi, lembaga, metode, risk_min, "dashboard")
        cached = self._dashboard_cache.get(key)
        if cached is not None:
            return cached

        where, params = build_where(
            provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
        )

        with self._lock:
            # Single scan: overview + signals
            stats = self.conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_paket,
                    COALESCE(SUM(pagu) / 1e9, 0) AS total_pagu_miliar,
                    SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS paket_kritis,
                    COALESCE(AVG(RPI), 0) AS avg_rpi,
                    SUM(CASE WHEN s3_fragmentasi >= 0.6 THEN 1 ELSE 0 END) AS split_contract,
                    AVG(s1_metode) AS s1,
                    AVG(s2_pagu_anomali) AS s2,
                    AVG(s3_fragmentasi) AS s3,
                    AVG(s4_konsentrasi) AS s4,
                    AVG(s5_umkm) AS s5,
                    AVG(s6_dana_metode) AS s6,
                    AVG(s7_reputasi) AS s7
                FROM packages
                WHERE {where}
                """,
                params,
            ).fetchone()

            risk_df = self.conn.execute(
                f"""
                SELECT risk_label, COUNT(*) AS count
                FROM packages WHERE {where}
                GROUP BY risk_label
                """,
                params,
            ).fetchdf()

            metode_df = self.conn.execute(
                f"""
                SELECT metode, COUNT(*) AS jumlah, ROUND(AVG(RPI), 2) AS avg_rpi
                FROM packages WHERE {where}
                GROUP BY metode ORDER BY avg_rpi DESC
                """,
                params,
            ).fetchdf()

            scatter_df = self.conn.execute(
                f"""
                SELECT RPI, risk_label, pagu / 1e9 AS pagu_miliar, paket, lembaga, metode
                FROM packages
                WHERE {where}
                USING SAMPLE 3000 ROWS
                """,
                params,
            ).fetchdf()

            rank_lem_df = self.conn.execute(
                f"""
                SELECT lembaga, ROUND(AVG(RPI), 2) AS avg_rpi,
                    SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
                    SUM(CASE WHEN risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi,
                    COUNT(*) AS n_paket
                FROM packages WHERE {where}
                GROUP BY lembaga ORDER BY avg_rpi DESC LIMIT 25
                """,
                params,
            ).fetchdf()

            choropleth_df = pd.DataFrame()
            rank_prov_df = pd.DataFrame()
            if GEO_LOOKUP_CSV.exists():
                ch_where, ch_params = build_where(
                    lembaga=lembaga, metode=metode, risk_min=risk_min, use_geo=True
                )
                choropleth_df = self.conn.execute(
                    f"""
                    SELECT
                        printf('%.2f', TRY_CAST(kabkot_id AS DOUBLE)) AS kabkot_id,
                        kabkot_name, prov_name,
                        COUNT(*) AS n_paket,
                        ROUND(AVG(RPI), 2) AS avg_rpi,
                        ROUND(SUM(pagu) / 1e9, 2) AS total_pagu_miliar,
                        SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
                        SUM(CASE WHEN risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi
                    FROM packages_geo
                    WHERE {ch_where}
                    GROUP BY kabkot_id, kabkot_name, prov_name
                    ORDER BY avg_rpi DESC
                    """,
                    ch_params,
                ).fetchdf()

                prov_where, prov_params = build_where(
                    lembaga=lembaga, metode=metode, risk_min=risk_min, use_geo=True
                )
                rank_prov_df = self.conn.execute(
                    f"""
                    SELECT prov_name, ROUND(AVG(RPI), 2) AS avg_rpi,
                        SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
                        SUM(CASE WHEN risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi,
                        COUNT(*) AS n_paket
                    FROM packages_geo
                    WHERE {prov_where}
                    GROUP BY prov_name ORDER BY avg_rpi DESC LIMIT 25
                    """,
                    prov_params,
                ).fetchdf()

        bundle = {
            "overview": {
                "total_paket": int(stats[0]),
                "total_pagu_miliar": round(float(stats[1]), 2),
                "paket_kritis": int(stats[2]),
                "avg_rpi": round(float(stats[3]), 2),
                "split_contract": int(stats[4]),
            },
            "signals": {
                "Metode": round(float(stats[5] or 0), 4),
                "Pagu Anomali": round(float(stats[6] or 0), 4),
                "Fragmentasi": round(float(stats[7] or 0), 4),
                "Konsentrasi": round(float(stats[8] or 0), 4),
                "UMKM": round(float(stats[9] or 0), 4),
                "Dana+Metode": round(float(stats[10] or 0), 4),
                "Reputasi KG": round(float(stats[11] or 0), 4),
            },
            "risk_distribution": risk_df.to_dict(orient="records"),
            "metode": metode_df.to_dict(orient="records"),
            "scatter": scatter_df.to_dict(orient="records"),
            "rank_lembaga": rank_lem_df.to_dict(orient="records"),
            "choropleth": choropleth_df.to_dict(orient="records"),
            "rank_provinsi": rank_prov_df.to_dict(orient="records"),
            "kg": self._kg_subset(lembaga),
        }
        self._dashboard_cache.set(key, bundle)
        return bundle

    def _kg_subset(self, lembaga: str) -> dict:
        if self._kg_nodes is None or self._kg_edges is None:
            return {"nodes": [], "edges": []}

        nodes_df = self._kg_nodes[self._kg_nodes["node_type"].isin(["lembaga", "satker"])]
        edges_df = self._kg_edges

        if lembaga and lembaga != "ALL":
            focus_id = f"L::{lembaga}"
            connected = edges_df[edges_df["source"] == focus_id]["target"].tolist()
            keep = set([focus_id] + connected)
            nodes_df = nodes_df[nodes_df["node_id"].isin(keep)]
        else:
            nodes_df = nodes_df.sort_values("risk_influence", ascending=False).head(70)

        node_ids = set(nodes_df["node_id"])
        edges_sub = edges_df[
            edges_df["source"].isin(node_ids) & edges_df["target"].isin(node_ids)
        ]
        return {
            "nodes": nodes_df.to_dict(orient="records"),
            "edges": edges_sub.to_dict(orient="records"),
        }

    def fetch_packages_page(
        self,
        provinsi: str,
        lembaga: str,
        metode: str,
        risk_min: float,
        page: int,
        page_size: int,
    ) -> dict:
        effective_risk = max(risk_min, 30)
        key = self._filter_cache_key(provinsi, lembaga, metode, effective_risk, f"p{page}s{page_size}")
        cached = self._packages_cache.get(key)
        if cached is not None:
            return cached

        where, params = build_where(
            provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=effective_risk
        )
        offset = (page - 1) * page_size

        with self._lock:
            total = int(
                self.conn.execute(
                    f"SELECT COUNT(*) FROM packages WHERE {where}", params
                ).fetchone()[0]
            )
            df = self.conn.execute(
                f"""
                SELECT id, RPI, risk_label, paket, lembaga, metode, pagu, lokasi,
                       s1_metode, s2_pagu_anomali, s3_fragmentasi, s4_konsentrasi,
                       s5_umkm, s6_dana_metode, s7_reputasi
                FROM packages
                WHERE {where}
                ORDER BY RPI DESC, id ASC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchdf()

        records = df.to_dict(orient="records")
        for rec in records:
            if rec.get("pagu") is not None:
                rec["pagu_miliar"] = round(float(rec["pagu"]) / 1e9, 3)

        total_pages = max(1, (total + page_size - 1) // page_size)
        result = {
            "data": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
        self._packages_cache.set(key, result)
        return result

    # Legacy helpers for individual endpoints
    def fetch_df(self, sql: str, params: list | None = None) -> pd.DataFrame:
        with self._lock:
            if params:
                return self.conn.execute(sql, params).fetchdf()
            return self.conn.execute(sql).fetchdf()

    def fetch_one(self, sql: str, params: list | None = None):
        with self._lock:
            if params:
                return self.conn.execute(sql, params).fetchone()
            return self.conn.execute(sql).fetchone()

    def load_kg_nodes(self) -> pd.DataFrame:
        if self._kg_nodes is None:
            raise FileNotFoundError(f"Missing {KG_NODES_CSV}")
        return self._kg_nodes

    def load_kg_edges(self) -> pd.DataFrame:
        if self._kg_edges is None:
            raise FileNotFoundError(f"Missing {KG_EDGES_CSV}")
        return self._kg_edges

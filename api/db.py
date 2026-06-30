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
    DATA_CHUNKS_DIR,
    DATA_CHUNKS_GLOB,
    DATA_NETWORK_CSV,
    DATA_NETWORK_PARQUET,
    DUCKDB_CACHE,
    GEO_LOOKUP_CSV,
    GEOJSON_PATH,
    KG_EDGES_CSV,
    KG_NODES_CSV,
)
from api.filters import build_where
from api.owner_category import MAP_MODES, OWNER_CATEGORY_EXPR


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
        self._geo_coverage_cache: dict | None = None
        self._geojson_cache: dict | None = None
        self._kg_nodes: pd.DataFrame | None = None
        self._kg_edges: pd.DataFrame | None = None
        self.source_path = ""
        self.source_kind = ""

        t0 = time.perf_counter()
        self._ensure_database()
        self.conn = duckdb.connect(str(DUCKDB_CACHE), read_only=False)
        self._configure_session()
        self._ensure_packages_geo(self.conn)
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
        chunks = list(DATA_CHUNKS_DIR.glob("*.parquet")) if DATA_CHUNKS_DIR.exists() else []
        if chunks:
            return max(f.stat().st_mtime for f in chunks)
        if DATA_NETWORK_PARQUET.exists():
            return DATA_NETWORK_PARQUET.stat().st_mtime
        if DATA_NETWORK_CSV.exists():
            return DATA_NETWORK_CSV.stat().st_mtime
        return 0

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, name: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [name],
        ).fetchone()
        return int(row[0]) > 0

    def _cache_is_usable(self) -> bool:
        """Cache exists, is newer than sources, and has the packages table."""
        if not DUCKDB_CACHE.exists():
            return False
        try:
            if DUCKDB_CACHE.stat().st_mtime < self._source_mtime():
                return False
            test_con = duckdb.connect(str(DUCKDB_CACHE), read_only=True)
            ok = self._table_exists(test_con, "packages")
            test_con.close()
            return ok
        except Exception:
            return False

    def _create_packages_geo(self, conn: duckdb.DuckDBPyConnection) -> None:
        if GEO_LOOKUP_CSV.exists():
            geo = GEO_LOOKUP_CSV.as_posix()
            conn.execute(
                f"""
                CREATE OR REPLACE TABLE geo_lookup AS
                SELECT * FROM read_csv_auto('{geo}', header=true)
                """
            )
            conn.execute(
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
            conn.execute(
                """
                CREATE TABLE packages_geo AS
                SELECT *, CAST(NULL AS VARCHAR) AS kabkot_id,
                       CAST(NULL AS VARCHAR) AS kabkot_name,
                       CAST(NULL AS VARCHAR) AS prov_name
                FROM packages WHERE 1=0
                """
            )

    def _ensure_packages_geo(self, conn: duckdb.DuckDBPyConnection) -> None:
        if self._table_exists(conn, "packages_geo"):
            return
        if not self._table_exists(conn, "packages"):
            raise RuntimeError("DuckDB cache is missing the packages table")
        print("[Auditra] Repairing cache: creating packages_geo table…")
        self._create_packages_geo(conn)

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
        if self._cache_is_usable():
            if DATA_CHUNKS_DIR.exists() and list(DATA_CHUNKS_DIR.glob("*.parquet")):
                self.source_path = str(DATA_CHUNKS_GLOB)
            else:
                self.source_path = str(
                    DATA_NETWORK_PARQUET if DATA_NETWORK_PARQUET.exists() else DATA_NETWORK_CSV
                )
            self.source_kind = "duckdb_cache"
            return

        chunks = list(DATA_CHUNKS_DIR.glob("*.parquet")) if DATA_CHUNKS_DIR.exists() else []
        if chunks:
            source_file = str(DATA_CHUNKS_GLOB.as_posix())
            self.source_path = source_file
            self.source_kind = "parquet_chunks"
        else:
            if not DATA_NETWORK_CSV.exists() and not DATA_NETWORK_PARQUET.exists():
                raise FileNotFoundError(
                    "Dataset utama belum ada. Jalankan pipeline:\n"
                    "  python 01_cleaning.py … python 03b_geo_matching.py"
                )

            parquet = self._ensure_parquet()
            source_file = str(parquet.as_posix())
            self.source_path = source_file
            self.source_kind = "parquet"

        building = DUCKDB_CACHE.with_suffix(".duckdb.building")
        for stale in (DUCKDB_CACHE, building):
            if stale.exists():
                stale.unlink()

        print("[Auditra] Building DuckDB cache (one-time, ~1-3 min)…")
        t0 = time.perf_counter()
        con = duckdb.connect(str(building))
        con.execute("SET threads TO 4")

        con.execute(
            f"""
            CREATE TABLE packages AS
            SELECT * FROM read_parquet('{source_file}')
            """
        )
        self._create_packages_geo(con)

        con.close()
        building.replace(DUCKDB_CACHE)
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

        self._geo_coverage_cache = self._compute_geo_coverage()

    def _compute_geo_coverage(self) -> dict:
        with self._lock:
            total = int(self.conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0])
            if not GEO_LOOKUP_CSV.exists() or total == 0:
                return {
                    "total_packages": total,
                    "mapped_packages": 0,
                    "unmapped_packages": total,
                    "multi_lokasi_packages": 0,
                }

            if not self._table_exists(self.conn, "packages_geo"):
                return {
                    "total_packages": total,
                    "mapped_packages": 0,
                    "unmapped_packages": total,
                    "multi_lokasi_packages": 0,
                }

            mapped = int(
                self.conn.execute(
                    "SELECT COUNT(DISTINCT id) FROM packages_geo"
                ).fetchone()[0]
            )
            multi = int(
                self.conn.execute(
                    """
                    SELECT COUNT(DISTINCT p.id)
                    FROM packages p
                    INNER JOIN (
                        SELECT lokasi_sirup
                        FROM geo_lookup
                        GROUP BY lokasi_sirup
                        HAVING COUNT(DISTINCT kabkot_id) > 1
                    ) m ON p.lokasi = m.lokasi_sirup
                    """
                ).fetchone()[0]
            )

        return {
            "total_packages": total,
            "mapped_packages": mapped,
            "unmapped_packages": max(0, total - mapped),
            "multi_lokasi_packages": multi,
        }

    def geo_coverage(self) -> dict:
        if self._geo_coverage_cache is None:
            self._geo_coverage_cache = self._compute_geo_coverage()
        return dict(self._geo_coverage_cache)

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
            provinsi=provinsi,
            lembaga=lembaga,
            metode=metode,
            risk_min=risk_min,
            packages_via_geo=GEO_LOOKUP_CSV.exists(),
        )

        with self._lock:
            # Single scan: overview + signals
            stats = self.conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_paket,
                    COALESCE(SUM(pagu) / 1e9, 0) AS total_pagu_miliar,
                    COALESCE(SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END), 0) AS paket_kritis,
                    COALESCE(AVG(RPI), 0) AS avg_rpi,
                    COALESCE(SUM(CASE WHEN s3_fragmentasi >= 0.6 THEN 1 ELSE 0 END), 0) AS split_contract,
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
                    SUM(CASE WHEN risk_label = 'KRITIS'
                        AND (s2_pagu_anomali >= 0.8 OR s3_fragmentasi >= 0.6)
                        THEN 1 ELSE 0 END) AS n_ekstrem,
                    ROUND(COALESCE(SUM(pagu) / 1e9, 0), 2) AS total_pagu_miliar,
                    COUNT(*) AS n_paket
                FROM packages WHERE {where}
                GROUP BY lembaga ORDER BY avg_rpi DESC LIMIT 100
                """,
                params,
            ).fetchdf()

            choropleth_df = pd.DataFrame()
            choropleth_modes: dict[str, list] = {m: [] for m in MAP_MODES}
            rank_prov_df = pd.DataFrame()
            if GEO_LOOKUP_CSV.exists():
                ch_where, ch_params = build_where(
                    lembaga=lembaga,
                    metode=metode,
                    risk_min=risk_min,
                    packages_geo=True,
                    table_prefix="pg.",
                )
                choropleth_modes = self._fetch_choropleth_modes(ch_where, ch_params)
                choropleth_df = pd.DataFrame(choropleth_modes.get("kl", []))

                prov_where, prov_params = build_where(
                    provinsi=provinsi,
                    lembaga=lembaga,
                    metode=metode,
                    risk_min=risk_min,
                    packages_geo=True,
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
                "total_paket": int(stats[0] or 0),
                "total_pagu_miliar": round(float(stats[1] or 0), 2),
                "paket_kritis": int(stats[2] or 0),
                "avg_rpi": round(float(stats[3] or 0), 2),
                "split_contract": int(stats[4] or 0),
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
            "choropleth_modes": choropleth_modes,
            "rank_provinsi": rank_prov_df.to_dict(orient="records"),
            "geo_coverage": self.geo_coverage(),
            "kg": self._kg_subset_safe(provinsi, lembaga, metode, risk_min),
        }
        self._dashboard_cache.set(key, bundle)
        return bundle

    def _fetch_choropleth_modes(self, where: str, params: list) -> dict[str, list]:
        """Agregat kab/kota per mode pemilik — seluruh Indonesia (tanpa filter provinsi)."""
        modes: dict[str, list] = {}
        with self._lock:
            for mode in MAP_MODES:
                df = self.conn.execute(
                    f"""
                    SELECT
                        printf('%.2f', TRY_CAST(pg.kabkot_id AS DOUBLE)) AS kabkot_id,
                        pg.kabkot_name,
                        pg.prov_name,
                        COUNT(*) AS n_paket,
                        ROUND(AVG(pg.RPI), 2) AS avg_rpi,
                        ROUND(SUM(pg.pagu) / 1e9, 2) AS total_pagu_miliar,
                        ROUND(SUM(CASE WHEN pg.RPI >= 50 THEN pg.pagu ELSE 0 END) / 1e9, 2)
                            AS pagu_risiko_miliar,
                        SUM(CASE WHEN pg.risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
                        SUM(CASE WHEN pg.risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi
                    FROM packages_geo pg
                    INNER JOIN packages p ON pg.id = p.id
                    WHERE {where} AND ({OWNER_CATEGORY_EXPR}) = ?
                    GROUP BY pg.kabkot_id, pg.kabkot_name, pg.prov_name
                    ORDER BY pagu_risiko_miliar DESC
                    """,
                    params + [mode],
                ).fetchdf()
                modes[mode] = df.to_dict(orient="records")
        return modes

    def _kg_subset_safe(
        self,
        provinsi: str = "ALL",
        lembaga: str = "ALL",
        metode: str = "ALL",
        risk_min: float = 0,
    ) -> dict:
        try:
            return self._kg_subset(provinsi, lembaga, metode, risk_min)
        except Exception as exc:
            print(f"[Auditra] KG subset gagal (filter tetap aktif): {exc}")
            return {"nodes": [], "edges": []}

    def _kg_subset(
        self,
        provinsi: str = "ALL",
        lembaga: str = "ALL",
        metode: str = "ALL",
        risk_min: float = 0,
    ) -> dict:
        if self._kg_nodes is None or self._kg_edges is None:
            return {"nodes": [], "edges": []}

        edges_df = self._kg_edges
        where, params = build_where(
            provinsi=provinsi,
            lembaga=lembaga,
            metode=metode,
            risk_min=risk_min,
            packages_via_geo=GEO_LOOKUP_CSV.exists(),
        )

        with self._lock:
            lem_stats = self.conn.execute(
                f"""
                SELECT lembaga AS label,
                       ROUND(AVG(RPI), 2) AS avg_rpi,
                       COUNT(*) AS n_paket
                FROM packages
                WHERE {where} AND lembaga IS NOT NULL
                GROUP BY lembaga
                """,
                params,
            ).fetchdf()
            sk_stats = self.conn.execute(
                f"""
                SELECT satker AS label,
                       ROUND(AVG(RPI), 2) AS avg_rpi,
                       COUNT(*) AS n_paket
                FROM packages
                WHERE {where} AND satker IS NOT NULL
                GROUP BY satker
                """,
                params,
            ).fetchdf()

        if lem_stats.empty and sk_stats.empty:
            return {"nodes": [], "edges": []}

        active_ids: set[str] = set()
        active_ids.update(f"L::{row['label']}" for _, row in lem_stats.iterrows())
        active_ids.update(f"SK::{row['label']}" for _, row in sk_stats.iterrows())

        nodes_df = self._kg_nodes[
            self._kg_nodes["node_type"].isin(["lembaga", "satker"])
            & self._kg_nodes["node_id"].isin(active_ids)
        ].copy()

        if nodes_df.empty:
            return {"nodes": [], "edges": []}

        lem_map = lem_stats.set_index("label")
        sk_map = sk_stats.set_index("label")

        def apply_live_stats(row: pd.Series) -> pd.Series:
            label = row["label"]
            if row["node_type"] == "lembaga" and label in lem_map.index:
                stats_row = lem_map.loc[label]
                row["avg_rpi"] = float(stats_row["avg_rpi"] or 0)
                row["n_paket"] = int(stats_row["n_paket"] or 0)
            elif row["node_type"] == "satker" and label in sk_map.index:
                stats_row = sk_map.loc[label]
                row["avg_rpi"] = float(stats_row["avg_rpi"] or 0)
                row["n_paket"] = int(stats_row["n_paket"] or 0)
            row["risk_influence"] = (
                float(row.get("avg_rpi") or 0) * int(row.get("n_paket") or 0) / 100.0
            )
            return row

        nodes_df = nodes_df.apply(apply_live_stats, axis=1)

        if lembaga and lembaga != "ALL":
            focus_id = f"L::{lembaga}"
            if focus_id not in set(nodes_df["node_id"]):
                return {"nodes": [], "edges": []}
            connected = edges_df[edges_df["source"] == focus_id]["target"].tolist()
            keep = {focus_id, *connected}
            nodes_df = nodes_df[nodes_df["node_id"].isin(keep)]
        else:
            nodes_df = nodes_df.sort_values(
                ["risk_influence", "avg_rpi"], ascending=False
            ).head(70)

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
            provinsi=provinsi,
            lembaga=lembaga,
            metode=metode,
            risk_min=effective_risk,
            packages_via_geo=GEO_LOOKUP_CSV.exists(),
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

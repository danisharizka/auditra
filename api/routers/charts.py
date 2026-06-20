from fastapi import APIRouter, HTTPException, Query

from api.db import DataStore
from api.filters import build_where

router = APIRouter(prefix="/api", tags=["charts"])


def _require_store() -> DataStore:
    try:
        return DataStore.get()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/charts/risk-distribution")
def risk_distribution(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    store = _require_store()
    where, params = build_where(
        provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
    )
    df = store.fetch_df(
        f"""
        SELECT risk_label, COUNT(*) AS count
        FROM packages
        WHERE {where}
        GROUP BY risk_label
        """,
        params,
    )
    return df.to_dict(orient="records")


@router.get("/charts/metode")
def metode_bar(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    store = _require_store()
    where, params = build_where(
        provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
    )
    df = store.fetch_df(
        f"""
        SELECT metode, COUNT(*) AS jumlah, AVG(RPI) AS avg_rpi
        FROM packages
        WHERE {where}
        GROUP BY metode
        ORDER BY avg_rpi DESC
        """,
        params,
    )
    df["avg_rpi"] = df["avg_rpi"].round(2)
    return df.to_dict(orient="records")


@router.get("/charts/scatter")
def scatter(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
    limit: int = Query(3000, ge=100, le=10000),
):
    """Random sample for visualization — COUNT/stats still use full filtered set."""
    store = _require_store()
    where, params = build_where(
        provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
    )
    df = store.fetch_df(
        f"""
        SELECT RPI, risk_label, pagu / 1e9 AS pagu_miliar, paket, lembaga, metode
        FROM packages
        WHERE {where}
        ORDER BY random()
        LIMIT ?
        """,
        params + [limit],
    )
    return {
        "points": df.to_dict(orient="records"),
        "note": f"Visual sample max {limit} points; aggregates use all matching rows.",
    }


@router.get("/charts/signals")
def signal_radar(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    store = _require_store()
    where, params = build_where(
        provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
    )
    row = store.fetch_one(
        f"""
        SELECT
            AVG(s1_metode) AS metode,
            AVG(s2_pagu_anomali) AS pagu_anomali,
            AVG(s3_fragmentasi) AS fragmentasi,
            AVG(s4_konsentrasi) AS konsentrasi,
            AVG(s5_umkm) AS umkm,
            AVG(s6_dana_metode) AS dana_metode,
            AVG(s7_reputasi) AS reputasi_kg
        FROM packages
        WHERE {where}
        """,
        params,
    )
    return {
        "Metode": round(float(row[0] or 0), 4),
        "Pagu Anomali": round(float(row[1] or 0), 4),
        "Fragmentasi": round(float(row[2] or 0), 4),
        "Konsentrasi": round(float(row[3] or 0), 4),
        "UMKM": round(float(row[4] or 0), 4),
        "Dana+Metode": round(float(row[5] or 0), 4),
        "Reputasi KG": round(float(row[6] or 0), 4),
    }


@router.get("/charts/choropleth")
def choropleth(
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    store = _require_store()
    if not store.meta()["geo_lookup_available"]:
        raise HTTPException(status_code=503, detail="geo_lookup.csv not found")

    where, params = build_where(
        lembaga=lembaga, metode=metode, risk_min=risk_min, use_geo=True
    )
    df = store.fetch_df(
        f"""
        SELECT
            printf('%.2f', TRY_CAST(g.kabkot_id AS DOUBLE)) AS kabkot_id,
            g.kabkot_name,
            g.prov_name,
            COUNT(*) AS n_paket,
            AVG(p.RPI) AS avg_rpi,
            SUM(p.pagu) / 1e9 AS total_pagu_miliar,
            SUM(CASE WHEN p.risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
            SUM(CASE WHEN p.risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi
        FROM packages p
        INNER JOIN geo_lookup g ON p.lokasi = g.lokasi_sirup
        WHERE {where}
        GROUP BY g.kabkot_id, g.kabkot_name, g.prov_name
        ORDER BY avg_rpi DESC
        """,
        params,
    )
    df["avg_rpi"] = df["avg_rpi"].round(2)
    df["total_pagu_miliar"] = df["total_pagu_miliar"].round(2)
    return df.to_dict(orient="records")


@router.get("/rankings/lembaga")
def rank_lembaga(
    provinsi: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
    limit: int = Query(25, ge=1, le=100),
):
    store = _require_store()
    where, params = build_where(
        provinsi=provinsi, metode=metode, risk_min=risk_min
    )
    df = store.fetch_df(
        f"""
        SELECT
            lembaga,
            AVG(RPI) AS avg_rpi,
            SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
            SUM(CASE WHEN risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi,
            COUNT(*) AS n_paket
        FROM packages
        WHERE {where}
        GROUP BY lembaga
        ORDER BY avg_rpi DESC
        LIMIT ?
        """,
        params + [limit],
    )
    df["avg_rpi"] = df["avg_rpi"].round(2)
    return df.to_dict(orient="records")


@router.get("/rankings/provinsi")
def rank_provinsi(
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
    limit: int = Query(25, ge=1, le=100),
):
    store = _require_store()
    if not store.meta()["geo_lookup_available"]:
        raise HTTPException(status_code=503, detail="geo_lookup.csv not found")

    where, params = build_where(
        lembaga=lembaga, metode=metode, risk_min=risk_min, use_geo=True
    )
    df = store.fetch_df(
        f"""
        SELECT
            g.prov_name,
            AVG(p.RPI) AS avg_rpi,
            SUM(CASE WHEN p.risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS n_kritis,
            SUM(CASE WHEN p.risk_label = 'TINGGI' THEN 1 ELSE 0 END) AS n_tinggi,
            COUNT(*) AS n_paket
        FROM packages p
        INNER JOIN geo_lookup g ON p.lokasi = g.lokasi_sirup
        WHERE {where}
        GROUP BY g.prov_name
        ORDER BY avg_rpi DESC
        LIMIT ?
        """,
        params + [limit],
    )
    df["avg_rpi"] = df["avg_rpi"].round(2)
    return df.to_dict(orient="records")

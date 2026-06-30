from fastapi import APIRouter, HTTPException, Query

from api.deps import require_store
from api.filters import build_where
from api.schemas import OverviewStats

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    try:
        store = require_store()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    where, params = build_where(
        provinsi=provinsi, lembaga=lembaga, metode=metode, risk_min=risk_min
    )
    row = store.fetch_one(
        f"""
        SELECT
            COUNT(*) AS total_paket,
            COALESCE(SUM(pagu) / 1e9, 0) AS total_pagu_miliar,
            SUM(CASE WHEN risk_label = 'KRITIS' THEN 1 ELSE 0 END) AS paket_kritis,
            COALESCE(AVG(RPI), 0) AS avg_rpi,
            SUM(CASE WHEN s3_fragmentasi >= 0.6 THEN 1 ELSE 0 END) AS split_contract
        FROM packages
        WHERE {where}
        """,
        params,
    )
    return OverviewStats(
        total_paket=int(row[0]),
        total_pagu_miliar=round(float(row[1]), 2),
        paket_kritis=int(row[2]),
        avg_rpi=round(float(row[3]), 2),
        split_contract=int(row[4]),
    )

from fastapi import APIRouter, HTTPException, Query

from api.db import DataStore

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/bundle")
def dashboard_bundle(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
):
    """
    Single request for all chart data — one DuckDB session, cached per filter combo.
    Replaces 9 separate API calls from the frontend.
    """
    try:
        store = DataStore.get()
        return store.fetch_dashboard_bundle(provinsi, lembaga, metode, risk_min)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

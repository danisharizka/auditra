from fastapi import APIRouter, HTTPException, Query

from api.deps import require_store
from api.schemas import PaginatedPackages

router = APIRouter(prefix="/api", tags=["packages"])


@router.get("/packages", response_model=PaginatedPackages)
def list_packages(
    provinsi: str = Query("ALL"),
    lembaga: str = Query("ALL"),
    metode: str = Query("ALL"),
    risk_min: float = Query(0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    try:
        store = require_store()
        return store.fetch_packages_page(
            provinsi, lembaga, metode, risk_min, page, page_size
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

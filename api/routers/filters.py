from fastapi import APIRouter, HTTPException, Query

from api.deps import require_store
from api.filters import build_where

router = APIRouter(prefix="/api", tags=["filters"])


@router.get("/filters/options")
def filter_options():
    try:
        store = require_store()
        return store.filter_options()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

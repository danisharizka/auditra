from fastapi import APIRouter, HTTPException

from api.db import DataStore
from api.deps import require_store
from api.schemas import MetaResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    ready = DataStore.is_ready()
    return {
        "status": "ok" if ready else "warming",
        "service": "auditra-api",
        "database_ready": ready,
    }


@router.get("/meta", response_model=MetaResponse)
def meta():
    try:
        store = require_store()
        return store.meta()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

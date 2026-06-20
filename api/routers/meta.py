from fastapi import APIRouter, HTTPException

from api.db import DataStore
from api.schemas import MetaResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "auditra-api"}


@router.get("/meta", response_model=MetaResponse)
def meta():
    try:
        store = DataStore.get()
        return store.meta()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

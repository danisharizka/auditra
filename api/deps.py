"""FastAPI dependencies shared across routers."""

from fastapi import HTTPException

from api.db import DataStore, DataStoreNotReady


def require_store() -> DataStore:
    try:
        return DataStore.get()
    except DataStoreNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

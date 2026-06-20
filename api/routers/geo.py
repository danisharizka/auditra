from fastapi import APIRouter, HTTPException

from api.db import DataStore

router = APIRouter(prefix="/api", tags=["geo"])


@router.get("/geo/kabkota")
def kabkota_geojson():
    try:
        store = DataStore.get()
        return store.geojson()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

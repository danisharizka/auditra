from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.db import DataStore
from api.routers import charts, dashboard, filters, geo, kg, meta, overview, packages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm DuckDB cache + default dashboard bundle on startup."""
    store = DataStore.get()
    store.fetch_dashboard_bundle()
    print("[Auditra] Startup warm-up complete.")
    yield


app = FastAPI(
    title="Auditra API",
    description=(
        "Backend dashboard Auditra. Data materialized in DuckDB untuk query cepat. "
        "Seluruh baris tetap utuh; API mengembalikan agregat/pagination."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(filters.router)
app.include_router(dashboard.router)
app.include_router(overview.router)
app.include_router(packages.router)
app.include_router(charts.router)
app.include_router(kg.router)
app.include_router(geo.router)

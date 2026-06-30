"""Auditra API configuration — paths resolve from project root."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_NETWORK_CSV = ROOT / "output" / "data_network.csv"
DATA_NETWORK_PARQUET = ROOT / "output" / "data_network.parquet"
DATA_CHUNKS_DIR = ROOT / "output" / "chunks"
DATA_CHUNKS_GLOB = DATA_CHUNKS_DIR / "*.parquet"
DUCKDB_CACHE = ROOT / "output" / "auditra.duckdb"
KG_NODES_CSV = ROOT / "output" / "kg_nodes.csv"
KG_EDGES_CSV = ROOT / "output" / "kg_edges.csv"
GEO_LOOKUP_CSV = ROOT / "geo" / "geo_lookup.csv"
GEOJSON_PATH = ROOT / "geo" / "kabkota_clean.geojson"

# LRU cache entries for dashboard bundles (per filter combo)
DASHBOARD_CACHE_SIZE = 64

_DEFAULT_CORS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _DEFAULT_CORS).split(",")
    if o.strip()
]

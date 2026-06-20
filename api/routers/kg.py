from fastapi import APIRouter, HTTPException, Query

from api.db import DataStore

router = APIRouter(prefix="/api", tags=["kg"])


@router.get("/kg")
def knowledge_graph(
    lembaga: str = Query("ALL"),
    max_nodes: int = Query(70, ge=10, le=200),
):
    try:
        store = DataStore.get()
        nodes_df = store.load_kg_nodes()
        edges_df = store.load_kg_edges()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    nodes_df = nodes_df[nodes_df["node_type"].isin(["lembaga", "satker"])]

    if lembaga and lembaga != "ALL":
        focus_id = f"L::{lembaga}"
        connected = edges_df[edges_df["source"] == focus_id]["target"].tolist()
        keep = set([focus_id] + connected)
        nodes_df = nodes_df[nodes_df["node_id"].isin(keep)]
    else:
        nodes_df = nodes_df.sort_values("risk_influence", ascending=False).head(max_nodes)

    node_ids = set(nodes_df["node_id"])
    edges_sub = edges_df[
        edges_df["source"].isin(node_ids) & edges_df["target"].isin(node_ids)
    ]

    return {
        "nodes": nodes_df.to_dict(orient="records"),
        "edges": edges_sub.to_dict(orient="records"),
    }

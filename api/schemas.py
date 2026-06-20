from pydantic import BaseModel


class MetaResponse(BaseModel):
    total_rows: int
    total_columns: int
    columns: list[str]
    source_file: str
    source_kind: str
    integrity: str
    note: str
    kg_nodes_available: bool
    kg_edges_available: bool
    geo_lookup_available: bool


class OverviewStats(BaseModel):
    total_paket: int
    total_pagu_miliar: float
    paket_kritis: int
    avg_rpi: float
    split_contract: int


class PaginatedPackages(BaseModel):
    data: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int

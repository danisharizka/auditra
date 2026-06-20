"""Shared SQL filter builder for dashboard queries."""

from __future__ import annotations


def build_where(
    *,
    provinsi: str = "ALL",
    lembaga: str = "ALL",
    metode: str = "ALL",
    risk_min: float = 0,
    use_geo: bool = False,
) -> tuple[str, list]:
    """Return SQL WHERE clause and bound parameters (safe from injection)."""
    clauses: list[str] = []
    params: list = []

    prefix = "" if not use_geo else "p."

    if provinsi and provinsi != "ALL":
        if use_geo:
            clauses.append("g.prov_name = ?")
            params.append(provinsi)
        else:
            clauses.append(f"{prefix}lokasi ILIKE ?")
            params.append(f"%{provinsi}%")

    if lembaga and lembaga != "ALL":
        clauses.append(f"{prefix}lembaga = ?")
        params.append(lembaga)

    if metode and metode != "ALL":
        clauses.append(f"{prefix}metode = ?")
        params.append(metode)

    if risk_min and risk_min > 0:
        clauses.append(f"{prefix}RPI >= ?")
        params.append(float(risk_min))

    return " AND ".join(clauses) if clauses else "1=1", params

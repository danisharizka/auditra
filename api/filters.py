"""Shared SQL filter builder for dashboard queries."""

from __future__ import annotations

# Alias UI / lokasi SIRUP → nama provinsi di geo_lookup (UPPERCASE)
PROVINSI_ALIASES: dict[str, str] = {
    "di yogyakarta": "DAERAH ISTIMEWA YOGYAKARTA",
    "diy": "DAERAH ISTIMEWA YOGYAKARTA",
    "daerah istimewa yogyakarta": "DAERAH ISTIMEWA YOGYAKARTA",
    "dki jakarta": "DKI JAKARTA",
    "jakarta": "DKI JAKARTA",
    "jawa barat": "JAWA BARAT",
    "jawa tengah": "JAWA TENGAH",
    "jawa timur": "JAWA TIMUR",
}


def resolve_provinsi(name: str) -> str:
    """Samakan variasi penulisan provinsi ke nama di geo_lookup."""
    key = name.strip().lower()
    return PROVINSI_ALIASES.get(key, name.strip())


def provinsi_match_sql(column: str) -> str:
    """Perbandingan provinsi case-insensitive (geo_lookup = UPPERCASE)."""
    return f"UPPER(TRIM({column})) = UPPER(TRIM(?))"


def build_where(
    *,
    provinsi: str = "ALL",
    lembaga: str = "ALL",
    metode: str = "ALL",
    risk_min: float = 0,
    use_geo: bool = False,
    packages_geo: bool = False,
    packages_via_geo: bool = False,
    table_prefix: str = "",
) -> tuple[str, list]:
    """Return SQL WHERE clause and bound parameters (safe from injection)."""
    clauses: list[str] = []
    params: list = []

    if packages_geo:
        pfx = table_prefix
        prov_col = f"{pfx}prov_name" if pfx else "prov_name"
    elif use_geo:
        pfx = "p."
        prov_col = "g.prov_name"
    else:
        pfx = table_prefix
        prov_col = "lokasi"

    if provinsi and provinsi != "ALL":
        resolved = resolve_provinsi(provinsi)
        if packages_via_geo and not packages_geo and not use_geo:
            id_col = f"{pfx}id" if pfx else "id"
            clauses.append(
                f"{id_col} IN (SELECT id FROM packages_geo WHERE {provinsi_match_sql('prov_name')})"
            )
            params.append(resolved)
        elif prov_col == "lokasi":
            patterns = list({f"%{resolved}%", f"%{provinsi.strip()}%"})
            if "yogyakarta" in resolved.lower():
                patterns.append("%DI Yogyakarta%")
            ors = " OR ".join(["lokasi ILIKE ?"] * len(patterns))
            clauses.append(f"({ors})")
            params.extend(patterns)
        else:
            clauses.append(provinsi_match_sql(prov_col))
            params.append(resolved)

    if lembaga and lembaga != "ALL":
        clauses.append(f"{pfx}lembaga = ?")
        params.append(lembaga)

    if metode and metode != "ALL":
        clauses.append(f"{pfx}metode = ?")
        params.append(metode)

    if risk_min and risk_min > 0:
        clauses.append(f"{pfx}RPI >= ?")
        params.append(float(risk_min))

    return " AND ".join(clauses) if clauses else "1=1", params

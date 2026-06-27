"""Klasifikasi pemilik paket SIRUP untuk mode peta (K/L · Pemprov · Pemkot · Lainnya)."""

from __future__ import annotations

# SQL expression → 'kl' | 'pemprov' | 'pemkot' | 'others'
# Gunakan alias tabel ``p`` untuk kolom packages (ownerType, lembaga).
OWNER_CATEGORY_EXPR = """
CASE
    WHEN COALESCE(p.ownerType, '') ILIKE '%kementerian%'
      OR COALESCE(p.ownerType, '') ILIKE '%lembaga%'
      OR COALESCE(p.ownerType, '') ILIKE '%k/l%'
      OR UPPER(TRIM(COALESCE(p.ownerType, ''))) IN ('KL', 'K/L', 'KEMENTERIAN/LEMBAGA')
      THEN 'kl'
    WHEN COALESCE(p.ownerType, '') ILIKE '%provinsi%'
      OR COALESCE(p.ownerType, '') ILIKE '%pemprov%'
      OR COALESCE(p.lembaga, '') ILIKE 'PEMERINTAH PROVINSI%'
      OR COALESCE(p.lembaga, '') ILIKE 'PEMPROV %'
      THEN 'pemprov'
    WHEN COALESCE(p.ownerType, '') ILIKE '%kabupaten%'
      OR COALESCE(p.ownerType, '') ILIKE '%kota%'
      OR COALESCE(p.ownerType, '') ILIKE '%pemkot%'
      OR COALESCE(p.ownerType, '') ILIKE '%pemkab%'
      OR COALESCE(p.ownerType, '') ILIKE '%daerah%'
      OR COALESCE(p.lembaga, '') ILIKE 'PEMERINTAH KABUPATEN%'
      OR COALESCE(p.lembaga, '') ILIKE 'PEMERINTAH KOTA%'
      OR COALESCE(p.lembaga, '') ILIKE 'PEMERINTAH DAERAH%'
      THEN 'pemkot'
    ELSE 'others'
END
"""

MAP_MODES = ("kl", "pemprov", "pemkot", "others")

MODE_LABELS = {
    "kl": "Kementerian/Lembaga",
    "pemprov": "Pemprov",
    "pemkot": "Pemkot/Kab",
    "others": "Lainnya",
}

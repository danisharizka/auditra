"""
Auditra - Step 3b: Geo Matching
Mencocokkan kolom 'lokasi' SIRUP (format: "Provinsi, Nama (Kab./Kota)")
ke GeoJSON 514 kabupaten/kota Indonesia.

Sumber GeoJSON: eppofahmi/geojson-indonesia (kota/all_kabkota_ind.geojson)

Output:
  - geo_lookup.csv      : mapping lokasi_sirup -> kabkota_id (untuk join cepat)
  - kabkota_clean.geojson : geojson dengan properties disederhanakan
  - unmatched_report.txt : daftar lokasi yang gagal di-match (untuk manual fix)
"""

import json
import re
import pandas as pd
from difflib import get_close_matches
import unicodedata

GEOJSON_PATH = 'kabkota.geojson'
DATA_PATH = 'output/data_network.csv'        # ganti sesuai lokasimu
OUTPUT_LOOKUP   = 'geo/geo_lookup.csv'
OUTPUT_GEOJSON  = 'geo/kabkota_clean.geojson'
OUTPUT_REPORT   = 'geo/unmatched_report.txt'

# ── Normalisasi teks ──────────────────────────────────────────────────────────
def normalize(s):
    if pd.isna(s):
        return ''
    s = str(s).upper()
    s = unicodedata.normalize('NFKD', s)
    s = re.sub(r'[^A-Z0-9\s]', ' ', s)
    s = re.sub(r'\bKAB\b|\bKABUPATEN\b', '', s)
    s = re.sub(r'\bKOTA\b', '', s)
    s = re.sub(r'\bADM\b|\bADMINISTRASI\b', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# Mapping provinsi pemekaran baru -> provinsi induk (geojson belum punya yang baru)
PROVINSI_PEMEKARAN = {
    'PAPUA TENGAH': 'PAPUA',
    'PAPUA PEGUNUNGAN': 'PAPUA',
    'PAPUA SELATAN': 'PAPUA',
    'PAPUA BARAT DAYA': 'PAPUA BARAT',
}

def normalize_provinsi(s):
    s = str(s).strip()
    # Fix DI Yogyakarta SEBELUM normalize umum (karena normalize() hapus titik)
    s = re.sub(r'^DI\s+Yogyakarta$', 'Daerah Istimewa Yogyakarta', s, flags=re.IGNORECASE)
    s_norm = normalize(s)
    if s_norm in PROVINSI_PEMEKARAN:
        s_norm = PROVINSI_PEMEKARAN[s_norm]
    return s_norm

# ── Load GeoJSON ──────────────────────────────────────────────────────────────
print("Loading geojson...")
with open(GEOJSON_PATH) as f:
    geo = json.load(f)

print(f"  Total features: {len(geo['features'])}")

# Build lookup table dari geojson: normalized_name -> kabkot_id
geo_lookup = []
for feat in geo['features']:
    props = feat['properties']
    geo_lookup.append({
        'kabkot_id':   f"{props['province_id']}.{props['kabkot_id']}",
        'prov_name':   props['prov_name'],
        'prov_norm':   normalize(props['prov_name']),
        'name':        props['name'],
        'name_norm':   normalize(props['name']),
        'alt_name':    props.get('alt_name', ''),
    })
df_geo = pd.DataFrame(geo_lookup)

# ── Load data SIRUP ───────────────────────────────────────────────────────────
print("\nLoading data SIRUP...")
df = pd.read_csv(DATA_PATH, low_memory=False, usecols=['lokasi'])
unique_lokasi = df['lokasi'].dropna().unique()
print(f"  Unique lokasi: {len(unique_lokasi)}")

# ── Parsing & Matching ────────────────────────────────────────────────────────
def parse_single_lokasi(loc_str):
    """Parse SATU lokasi 'Provinsi, Nama (Kab./Kota)' -> (provinsi, nama_kabkota)"""
    parts = str(loc_str).split(',', 1)
    if len(parts) != 2:
        return None, None
    provinsi = parts[0].strip()
    rest = parts[1].strip()
    nama = re.sub(r'\s*\((Kab\.?|Kota)\)\s*$', '', rest).strip()
    nama = re.sub(r'\(Kab\)$', '', nama).strip()  # handle "Sijunjung(Kab)" tanpa spasi/titik
    return provinsi, nama

def split_multi_lokasi(lokasi):
    """Paket bisa punya banyak lokasi dipisah '|'. Return list of (provinsi, nama)."""
    raw_parts = str(lokasi).split('|')
    parsed = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        provinsi, nama = parse_single_lokasi(part)
        if provinsi:
            parsed.append((provinsi, nama))
    return parsed

# Alias manual untuk nama lama/gabungan yang sudah berubah di geojson modern
MANUAL_ALIAS = {
    'SANGIHE TALAUD': 'KEPULAUAN SANGIHE',  
    'MERANTI': 'KEPULAUAN MERANTI',
    'SELAYAR': 'KEPULAUAN SELAYAR',
    'TALIABU': 'PULAU TALIABU',
    'PALI': 'PENUKAL ABAB LEMATANG ILIR',
    'PASANGKAYU': 'MAMUJU UTARA',  # GeoJSON seringkali masih menggunakan nama lama ini
}

def apply_manual_alias(nama_norm):
    return MANUAL_ALIAS.get(nama_norm, nama_norm)

# Lokasi yang memang TIDAK punya representasi geografis di Indonesia
# (luar negeri, kategori administratif umum) - skip tanpa dianggap error
NON_GEO_KEYWORDS = {'LAINNYA', 'LUAR INDONESIA', 'LUAR NEGERI'}

def is_non_geo(provinsi, nama):
    p = normalize(provinsi)
    n = normalize(nama)
    return p in NON_GEO_KEYWORDS or n in NON_GEO_KEYWORDS or p == '' or n == ''

def match_one(provinsi, nama, df_geo):
    """Match satu pasangan (provinsi, nama) ke geojson. Return dict atau None."""
    prov_norm = normalize_provinsi(provinsi)
    nama_norm = apply_manual_alias(normalize(nama))

    candidates = df_geo[df_geo['prov_norm'] == prov_norm]
    if len(candidates) == 0:
        all_provs = df_geo['prov_norm'].unique().tolist()
        close = get_close_matches(prov_norm, all_provs, n=1, cutoff=0.7)
        if close:
            candidates = df_geo[df_geo['prov_norm'] == close[0]]

    # ── Tahap 1: match dalam provinsi yang tertulis ──
    if len(candidates) > 0:
        exact = candidates[candidates['name_norm'] == nama_norm]
        if len(exact) > 0:
            row = exact.iloc[0]
            return {'kabkot_id': row['kabkot_id'], 'kabkot_name': row['name'],
                    'prov_name': row['prov_name'], 'match_type': 'exact'}

        cand_names = candidates['name_norm'].tolist()
        close = get_close_matches(nama_norm, cand_names, n=1, cutoff=0.75)
        if close:
            row = candidates[candidates['name_norm'] == close[0]].iloc[0]
            return {'kabkot_id': row['kabkot_id'], 'kabkot_name': row['name'],
                    'prov_name': row['prov_name'], 'match_type': 'fuzzy'}

    # ── Tahap 2: FALLBACK cross-provinsi ──
    # Data SIRUP kadang salah input provinsi (mis. "DKI Jakarta, Bulungan (Kab.)"
    # padahal Bulungan ada di Kalimantan Utara). Cari nama kab/kota itu di SELURUH
    # Indonesia; kalau ketemu unik (cuma 1 kandidat), pakai itu dan tandai sebagai
    # 'cross_province' supaya tetap bisa diaudit/dicek manual kalau perlu.
    exact_all = df_geo[df_geo['name_norm'] == nama_norm]
    if len(exact_all) == 1:
        row = exact_all.iloc[0]
        return {'kabkot_id': row['kabkot_id'], 'kabkot_name': row['name'],
                'prov_name': row['prov_name'], 'match_type': 'cross_province_exact'}

    all_names = df_geo['name_norm'].unique().tolist()
    close_all = get_close_matches(nama_norm, all_names, n=1, cutoff=0.85)  # cutoff lebih ketat krn lintas-provinsi
    if close_all:
        rows = df_geo[df_geo['name_norm'] == close_all[0]]
        if len(rows) == 1:
            row = rows.iloc[0]
            return {'kabkot_id': row['kabkot_id'], 'kabkot_name': row['name'],
                    'prov_name': row['prov_name'], 'match_type': 'cross_province_fuzzy'}

    return None

print("\nMatching lokasi ke geojson (termasuk paket multi-lokasi)...")
results = []
unmatched = []
skipped_non_geo = []

for lokasi in unique_lokasi:
    sub_locations = split_multi_lokasi(lokasi)

    if not sub_locations:
        unmatched.append((lokasi, 'PARSE_FAILED'))
        continue

    matched_kabkot = []
    failed_subs = []
    has_real_failure = False

    for provinsi, nama in sub_locations:
        if is_non_geo(provinsi, nama):
            skipped_non_geo.append(f"{provinsi} | {nama}")
            continue

        m = match_one(provinsi, nama, df_geo)
        if m:
            matched_kabkot.append(m)
        else:
            failed_subs.append(f"{provinsi} | {nama}")
            has_real_failure = True

    if matched_kabkot:
        # Simpan SEMUA kabkot yang match untuk lokasi ini (multi-lokasi paket)
        for m in matched_kabkot:
            results.append({
                'lokasi_sirup': lokasi,
                'n_lokasi_in_paket': len(sub_locations),
                'kabkot_id': m['kabkot_id'],
                'kabkot_name': m['kabkot_name'],
                'prov_name': m['prov_name'],
                'match_type': m['match_type'],
            })
        if has_real_failure:
            unmatched.append((lokasi, f"PARTIAL_MATCH, gagal: {'; '.join(failed_subs)}"))
    elif has_real_failure:
        unmatched.append((lokasi, f"NO_MATCH: {'; '.join(failed_subs)}"))
    else:
        # Semua sub-lokasi adalah non-geo (mis. seluruhnya "Lainnya, Luar Indonesia")
        # — bukan kegagalan, cuma tidak punya representasi peta.
        pass

df_lookup = pd.DataFrame(results)

# ── Summary ───────────────────────────────────────────────────────────────────
n_lokasi_matched = df_lookup['lokasi_sirup'].nunique() if len(df_lookup) > 0 else 0
n_skipped_unique = len(set(skipped_non_geo))
print(f"\nTotal lokasi unik (string SIRUP) : {len(unique_lokasi)}")
print(f"Berhasil di-match (≥1 kabkota)   : {n_lokasi_matched} ({n_lokasi_matched/len(unique_lokasi)*100:.1f}%)")
print(f"  - exact match rows           : {(df_lookup['match_type']=='exact').sum() if len(df_lookup)>0 else 0}")
print(f"  - fuzzy match rows           : {(df_lookup['match_type']=='fuzzy').sum() if len(df_lookup)>0 else 0}")
print(f"  - cross-province exact rows  : {(df_lookup['match_type']=='cross_province_exact').sum() if len(df_lookup)>0 else 0}  (provinsi SIRUP keliru, dikoreksi otomatis)")
print(f"  - cross-province fuzzy rows  : {(df_lookup['match_type']=='cross_province_fuzzy').sum() if len(df_lookup)>0 else 0}")
print(f"Total baris lookup (termasuk multi-lokasi) : {len(df_lookup)}")
print(f"Sub-lokasi non-geografis (Luar Indonesia/Lainnya), di-skip : {n_skipped_unique}")
print(f"Lokasi gagal total/parsial di-match (REAL FAILURE) : {len(unmatched)}")

# ── Save lookup ───────────────────────────────────────────────────────────────
df_lookup.to_csv(OUTPUT_LOOKUP, index=False)
print(f"\n✓ Saved lookup → {OUTPUT_LOOKUP}")

# ── Save cleaned geojson (properties disederhanakan) ──────────────────────────
clean_features = []
for feat in geo['features']:
    props = feat['properties']
    clean_features.append({
        'type': 'Feature',
        'properties': {
            'kabkot_id': f"{props['province_id']}.{props['kabkot_id']}",
            'name': props['name'],
            'prov_name': props['prov_name'],
        },
        'geometry': feat['geometry'],
    })

clean_geo = {'type': 'FeatureCollection', 'features': clean_features}
with open(OUTPUT_GEOJSON, 'w') as f:
    json.dump(clean_geo, f)
print(f"✓ Saved geojson → {OUTPUT_GEOJSON}")

# ── Save unmatched report ─────────────────────────────────────────────────────
with open(OUTPUT_REPORT, 'a', encoding='utf-8') as f:
    f.write(f"UNMATCHED LOCATIONS REPORT\n")
    f.write(f"Total: {len(unmatched)}\n\n")
    for lokasi, reason in unmatched:
        f.write(f"{lokasi}  →  {reason}\n")
print(f"✓ Saved unmatched report → {OUTPUT_REPORT}")

if unmatched:
    print(f"\n⚠ {len(unmatched)} lokasi gagal di-match. Cek {OUTPUT_REPORT}")
    print("  Contoh:")
    for lokasi, reason in unmatched[:10]:
        print(f"    {lokasi} → {reason}")
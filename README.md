# Auditra

**Sistem Prioritas Audit Pengadaan Publik** berbasis Knowledge Graph dan analisis jaringan — menggunakan data SIRUP (~3 juta paket) untuk membantu auditor menentukan paket mana yang paling mendesak diperiksa.

> RPI (Risk Priority Index) = alat **prioritas**, bukan vonis. Setiap skor dapat ditelusuri ke 7 sinyal risiko yang transparan.

## Untuk Juri / Reviewer

| Dokumen | Isi |
|---------|-----|
| [docs/CHECKLIST_JURI_SEC.md](docs/CHECKLIST_JURI_SEC.md) | Pemetaan kriteria SEC Satria Data + jawaban antisipasi |
| [docs/METODOLOGI.md](docs/METODOLOGI.md) | Algoritma step-by-step + dasar regulasi |
| [docs/DATA_SCIENCE.md](docs/DATA_SCIENCE.md) | Lifecycle sains data (EDA → deploy) |
| [docs/SUMBER_DATA.md](docs/SUMBER_DATA.md) | Provenance data SIRUP |

## Statistik Utama (verified)

| Metrik | Nilai |
|--------|-------|
| Baris dataset final | **3.002.992** |
| Kolom | **32** |
| Lembaga | 662 |
| Satker | 34.602 |
| Node Knowledge Graph | 35.320 |
| Edge KG | 207.427 |
| Paket KRITIS (RPI ≥ 70) | 568 (post-KG) |
| Geo match rate | 99,2% lokasi unik (46 edge case → `geo/unmatched_report.txt`) |

Verifikasi runtime: `GET http://127.0.0.1:8000/api/meta`

## Pipeline Analisis

```powershell
pip install -r requirements.txt
python run_pipeline.py
```

| Step | Script | Output |
|------|--------|--------|
| 0 | `00_eda.py` | `output/reports/eda_*` |
| 1 | `01_cleaning.py` | `data/data_clean.csv` |
| 1b | `01b_patch_lembaga_provinsi.py` | patch DQ |
| 2 | `02_scoring.py` | `output/data_scored.csv` + 7 sinyal RPI |
| 3 | `03_network_analysis.py` | KG + `output/data_network.csv` |
| 3b | `03b_geo_matching.py` | `geo/geo_lookup.csv` |
| 5 | `05_validate.py` | QA gate |
| 6 | `06_sensitivity_analysis.py` | robustness bobot RPI |

## Dashboard Web

```powershell
pip install -r requirements-web.txt
uvicorn api.main:app --reload --port 8000

cd web && npm install && npm run dev
```

Buka http://localhost:5173 — detail di [WEB.md](WEB.md).

## Teknik Sains Data yang Digunakan

- **EDA**: profil, missing value, IQR outlier, distribusi kategorikal
- **Preprocessing**: deduplikasi, normalisasi, data quality patch
- **Statistik**: z-score anomali pagu, persentil, agregasi
- **NLP**: TF-IDF + cosine similarity (deteksi fragmentasi/split contract)
- **Graph**: NetworkX — centrality, betweenness, community detection (modularity)
- **Geo-spatial**: fuzzy matching lokasi → kab/kota GeoJSON
- **Serving**: DuckDB materialized cache, agregat penuh ke API (bukan sample, kecuali scatter max 3.000 titik)

## Lisensi & Data

Kode: repositori ini. Data SIRUP: [LKPP](https://sirup.lkpp.go.id/) — tidak di-commit (`.gitignore`). GeoJSON: [eppofahmi/geojson-indonesia](https://github.com/eppofahmi/geojson-indonesia).

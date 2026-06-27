# Auditra Web Dashboard (FastAPI + React)

Stack **Opsi A**: Python backend + React frontend. **Seluruh 3 juta baris tetap utuh** di file sumber; API hanya mengirim agregat/pagination ke browser.

## Integritas data

| Lapisan | Isi |
|---|---|
| `output/data_network.csv` | **100% baris & kolom** pipeline (di `.gitignore`) |
| DuckDB | Query tanpa memotong source file |
| `GET /api/meta` | Verifikasi `total_rows` & `total_columns` |
| `GET /api/packages?page=N` | Akses **semua** baris via pagination (50/halaman) |
| Browser | Hanya terima JSON ringkas untuk chart/tabel |

Satu-satunya "sample" eksplisit: **scatter chart** (max 3.000 titik random untuk performa). Stat cards, peta, ranking, dan tabel menghitung dari **seluruh** baris yang match filter.

## Prasyarat

1. Jalankan pipeline (dari root proyek):

```powershell
# Pastikan data mentah ada di data/year-2026_merged.csv
pip install -r requirements.txt
python run_pipeline.py          # EDA → cleaning → scoring → KG → geo → validation

# Atau manual per-step — lihat docs/DATA_SCIENCE.md
```

2. (Opsional, lebih cepat) Export Parquet:

```powershell
python scripts/export_parquet.py
```

## Install & run

**Terminal 1 — API:**

```powershell
cd C:\GALIH\CODING\AUDITRA
pip install -r requirements-web.txt
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: http://127.0.0.1:8000/docs

**Terminal 2 — Frontend:**

```powershell
cd C:\GALIH\CODING\AUDITRA\web
npm install
npm run dev
```

Buka: http://localhost:5173

## Struktur

```
api/           FastAPI + DuckDB
web/           React + Vite + Tailwind + ECharts + Plotly
scripts/       export_parquet.py
01-06_*.py       Pipeline analisis
```

## Performa (optimasi v1.1)

Backend mem-materialize data ke `output/auditra.duckdb` + `output/data_network.parquet` (auto, sekali saja).

| Operasi | Sebelum | Sesudah |
|---|---|---|
| Ganti filter (9 request CSV) | 10–60+ detik | **~0,3 detik** (1 request bundle) |
| Filter sama lagi | 10–60+ detik | **instant** (cache) |
| Pagination tabel | beberapa detik | **~0,03 detik** |

**First run** setelah clone: startup API ~15–60 detik (build parquet + duckdb). Run berikutnya: ~2 detik.

Endpoint utama: `GET /api/dashboard/bundle` — menggantikan 9 call terpisah.

## Deploy production

Frontend bisa **Vercel**; backend **tidak** (butuh DuckDB + file besar). Panduan lengkap: [docs/DEPLOY.md](docs/DEPLOY.md).


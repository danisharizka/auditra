# Data folder

Taruh file mentah SIRUP di sini:

- `year-2026_merged.csv` — input pipeline (tidak di-commit ke GitHub)

## Pipeline lengkap

```powershell
pip install -r requirements.txt
python run_pipeline.py
```

Atau step-by-step — lihat `docs/DATA_SCIENCE.md`.

## Output

| Tahap | Output |
|-------|--------|
| EDA | `output/reports/eda_report.md` |
| Cleaning | `data/data_clean.csv` |
| Scoring | `output/data_scored.csv` |
| Network | `output/data_network.csv` |
| Geo | `geo/geo_lookup.csv` |
| Validation | `output/reports/validation_report.txt` |

File besar di `.gitignore` — simpan lokal atau cloud storage.

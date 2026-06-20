# Deploy Auditra

Arsitektur **split**: frontend static + backend Python dengan data besar.

```
[Vercel]  React (web/dist)     ──HTTPS──▶  [Railway/Render/VPS]  FastAPI + DuckDB
                                              ↑
                                    output/auditra.duckdb (~500MB–2GB)
                                    geo/kabkota_clean.geojson
```

---

## Bisa pakai Vercel?

| Komponen | Vercel? | Alasan |
|----------|---------|--------|
| **Frontend** (`web/`) | ✅ **Ya** | Static React/Vite — ideal untuk Vercel |
| **Backend** (`api/`) | ❌ **Tidak** | DuckDB + file 1GB+ butuh disk persisten & proses long-running |
| **Pipeline Python** | ❌ | Jalankan lokal/CI, upload hasil `output/` ke server |

Vercel serverless: limit ukuran deployment, **tidak ada disk persisten**, timeout function — tidak cocok untuk query 3 juta baris via DuckDB.

---

## Opsi deploy (disarankan)

### Opsi A — Vercel + Railway (paling mudah untuk demo)

**1. Backend di [Railway](https://railway.app) atau [Render](https://render.com)**

Persiapan file data (setelah `python run_pipeline.py`):

```
output/auditra.duckdb      ← wajib (atau parquet + auto-build saat startup)
output/data_network.parquet
geo/geo_lookup.csv
geo/kabkota_clean.geojson
output/kg_nodes.csv
output/kg_edges.csv
```

Upload via volume/persistent disk atau commit ke private storage lalu download saat build.

**Start command:**

```bash
pip install -r requirements-web.txt && uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

**Environment variables (backend):**

```
CORS_ORIGINS=https://auditra.vercel.app,https://your-team.vercel.app
```

**2. Frontend di Vercel**

- Root directory: `web`
- Framework: Vite
- Build: `npm run build`
- Output: `dist`

**Environment variables (Vercel):**

```
VITE_API_URL=https://YOUR-BACKEND.up.railway.app/api
```

Deploy → buka URL Vercel → dashboard memanggil API Railway.

---

### Opsi B — Satu VPS (DigitalOcean / AWS EC2 / IDCloudHost)

Cocok untuk presentasi final Satria Data (stabil, tidak cold start).

```bash
# Di VPS Ubuntu
git clone <repo>
cd AUDITRA
pip install -r requirements-web.txt
# upload output/ + geo/ ke server

# Frontend build
cd web && npm ci && npm run build

# Serve API (port 8000)
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Serve static (nginx) dari web/dist, proxy /api → :8000
```

Nginx contoh:

```nginx
server {
    listen 80;
    server_name auditra.example.com;

    root /var/www/auditra/web/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Dengan opsi ini **tidak perlu Vercel** — satu domain untuk semua.

---

### Opsi C — Demo lokal (presentasi juri)

Paling aman untuk final:

```powershell
# Terminal 1
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2
cd web && npm run dev
```

Atau build + preview:

```powershell
cd web
$env:VITE_API_URL="http://127.0.0.1:8000/api"
npm run build && npm run preview
```

---

## Checklist sebelum deploy

- [ ] Pipeline selesai: `python run_pipeline.py`
- [ ] `output/auditra.duckdb` ada di server backend
- [ ] `CORS_ORIGINS` berisi domain frontend production
- [ ] `VITE_API_URL` di Vercel mengarah ke `/api` backend (dengan prefix `/api`)
- [ ] Tes: `curl https://BACKEND/api/meta` → `total_rows: 3002992`

---

## Ukuran & biaya (perkiraan)

| Resource | Ukuran |
|----------|--------|
| `auditra.duckdb` | ~500 MB – 2 GB |
| `web/dist` | ~5–15 MB |
| RAM backend | min **2 GB** (disarankan 4 GB) |

Railway/Render free tier mungkin kurang RAM — upgrade atau pakai VPS untuk demo 3M baris.

---

## Yang tidak perlu di-deploy

- `data/year-2026_merged.csv` (mentah 1GB+) — hanya untuk pipeline
- `node_modules/`, `__pycache__/`
- Script pipeline `01_*.py` … (kecuali mau re-run di server)

---

## Troubleshooting

| Gejala | Penyebab | Fix |
|--------|----------|-----|
| CORS error di browser | Backend belum allow origin Vercel | Set `CORS_ORIGINS` |
| `Dataset belum siap` | DuckDB tidak ada di server | Upload `output/auditra.duckdb` |
| Dashboard kosong | `VITE_API_URL` salah | Harus `https://host/api` bukan tanpa `/api` |
| API lambat first hit | Cold start + warm DuckDB | Tunggu 30–60s atau keep-alive |

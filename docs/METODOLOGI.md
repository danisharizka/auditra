# Metodologi Auditra — Step by Step

Dokumen ini melengkapi esai SEC: algoritma ditulis eksplisit agar juri dapat menelusuri setiap langkah.

---

## 1. Sumber Data

Lihat [SUMBER_DATA.md](SUMBER_DATA.md).

---

## 2. Exploratory Data Analysis (Step 0)

**Input:** `data/year-2026_merged.csv` (N = 3.009.760 baris)

1. Profil dimensi, tipe data, missing value per kolom
2. Statistik deskriptif `pagu`: mean, median, kuartil, IQR outlier
3. Distribusi frekuensi: `metode`, `jenisPengadaan`, `lembaga`
4. Identifikasi duplikat `id`, pagu ≤ 0

**Output:** `output/reports/eda_report.md`, `eda_stats.json`, `eda_charts.html`

---

## 3. Preprocessing (Step 1–1b)

1. **Seleksi kolom** — hanya field SIRUP murni; drop enrichment pihak ketiga
2. **Deduplikasi** — `drop_duplicates(id)`
3. **Filter validitas** — `pagu > 0`
4. **Normalisasi teks** — strip whitespace
5. **Encoding kategori** — varian APBN → `sumberDana_cat = 'APBN'`
6. **Patch DQ** — hapus baris `lembaga` = nama provinsi polos (artefak SIRUP)

**Hasil:** N = 3.002.992 baris × 17 kolom

---

## 4. Feature Engineering — 7 Sinyal Risiko (Step 2)

### S1 — Metode Pemilihan (bobot 20%)

Mapping rule-based berdasarkan hierarki risiko tata kelola (PP 12/2019):

| Metode | Skor |
|--------|------|
| Penunjukan Langsung | 1.00 |
| Dikecualikan | 0.85 |
| Pengadaan Langsung | 0.40 |
| Tender Cepat | 0.30 |
| E-Purchasing | 0.20 |
| Seleksi | 0.10 |
| Tender | 0.05 |

### S2 — Anomali Pagu (bobot 20%)

Grup: `(jenisPengadaan, metode)`

\[
z = \frac{\log(1 + \text{pagu}) - \mu_{\text{grup}}}{\sigma_{\text{grup}} + \epsilon}, \quad s_2 = \frac{\clip(z, 0, 3)}{3}
\]

### S3 — Fragmentasi / Split Contract (bobot 15%)

**Kandidat:** Pengadaan Langsung, pagu ≤ Rp 200 juta, uraian tidak null

1. TF-IDF (`max_features=5000`, n-gram 1–2) pada `uraianPekerjaan`
2. Cosine similarity antar paket **dalam satker yang sama**
3. Jika max similarity ≥ 0,6 → skor = similarity

**Dasar regulasi:** batas PL Rp 200 juta (Perpres 16/2018) — pemecahan paket untuk menghindari tender.

### S4 — Konsentrasi Metode Berisiko per Satker (bobot 15%)

\[
r = \frac{\#\text{Penunjukan/Dikecualikan}}{\#\text{total paket satker}}, \quad s_4 = \clip(r / P_{95}(r), 0, 1)
\]

### S5 — Anomali UMKM (bobot 10%)

Jika `isUMKM=True` dan pagu > P90 pagu UMKM:

\[
s_5 = \min\left(\frac{\text{pagu}/P_{90} - 1}{9}, 1\right)
\]

### S6 — Kombinasi Dana + Metode (bobot 10%)

Matriks rule: APBN × metode berisiko → skor 0–1

### S7 — Reputasi Lembaga via KG (bobot 10%)

Tahap awal: rata-rata S1–S6 per lembaga.  
Tahap final (post network analysis):

\[
\text{risk\_influence} = \frac{w_{\text{degree}}}{w_{\max}} \times \frac{\overline{\text{RPI}}_{\text{lembaga}}}{100}
\]

---

## 5. Risk Priority Index (RPI)

\[
\text{RPI} = 100 \times \sum_{i=1}^{7} w_i \cdot s_i
\]

| Label | Threshold |
|-------|-----------|
| KRITIS | RPI ≥ 70 |
| TINGGI | RPI ≥ 50 |
| SEDANG | RPI ≥ 30 |
| RENDAH | RPI < 30 |

Bobot \(w_i\) di `config/pipeline.yaml`.

---

## 6. Knowledge Graph (Step 3)

**Node:** lembaga, satker, metode, jenis pengadaan, provinsi  
**Edge:** HAS_SATKER, USES_METHOD, PROCURES, OPERATES_IN (weight = jumlah paket)

**Metrik:**
- Degree centrality, in-degree centrality
- Weighted degree (normalisasi → `kg_pagerank`)
- Betweenness (subgraph lembaga–satker)
- Risk influence = weighted degree × avg RPI
- **Community detection:** greedy modularity (36 cluster lembaga)

S7 dan RPI di-recalculate setelah metrik KG.

---

## 7. Geo-Spatial Matching (Step 3b)

1. Parse `lokasi` → (provinsi, kab/kota)
2. Normalisasi Unicode + fuzzy match ke GeoJSON 514 kab/kota
3. Output `geo/geo_lookup.csv` untuk join cepat di API

**Limitasi:** 46 string lokasi multi-wilayah gagal sebagian (`geo/unmatched_report.txt`).

---

## 8. Validasi (Step 5)

Automated QA: row count integrity, RPI ∈ [0,100], duplikat id, kolom wajib.

---

## 9. Serving & Visualisasi

- DuckDB materialized cache — query agregat 3M baris ~0,2 detik
- Dashboard React: peta choropleth, KG, ranking, tabel paginated
- **Integritas:** `GET /api/meta` verifikasi N baris

---

## Referensi Regulasi & Metode

1. PP No. 12 Tahun 2019 — Pengadaan Barang/Jasa Pemerintah  
2. Perpres No. 16 Tahun 2018 — Pengadaan Barang/Jasa (batas PL)  
3. SIRUP — LKPP (https://sirup.lkpp.go.id/)  
4. Salton & McGill (1983) — TF-IDF  
5. Brandes (2001) — Betweenness centrality  
6. Clauset, Newman & Moore (2004) — Greedy modularity  

---

## Limitasi (Wajib Dijelaskan ke Juri)

1. **Bukan prediksi fraud** — prioritization heuristic  
2. **Bobot RPI** — expert judgment, bukan estimasi ML  
3. **S3 O(n²) per satker** — hanya kandidat PL ≤ 200 juta  
4. **Geo pemekaran** — Papua/Taliabu dll. belum di GeoJSON lama  
5. **Data SIRUP** — self-declared, belum verifikasi lapangan

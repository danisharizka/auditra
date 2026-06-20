# Sumber Data — Provenance

## Data Utama

| Atribut | Nilai |
|---------|-------|
| **Nama** | SIRUP (Sistem Informasi Rencana Umum Pengadaan) |
| **Penyedia** | LKPP — Lembaga Kebijakan Pengadaan Barang/Jasa Pemerintah |
| **URL** | https://sirup.lkpp.go.id/ |
| **File lokal** | `data/year-2026_merged.csv` |
| **Periode** | Rencana pengadaan 2026 |
| **Baris mentah** | 3.009.760 |
| **Baris setelah cleaning** | 3.002.992 |
| **Kolom dipakai** | 16 field SIRUP murni (+ 1 derived) |

## Kolom yang Digunakan

`id`, `paket`, `jenisPengadaan`, `metode`, `lembaga`, `satker`, `lokasi`, `pagu`, `pemilihanDate`, `sumberDana`, `isUMKM`, `volumePekerjaan`, `uraianPekerjaan`, `spesifikasiPekerjaan`, `ownerType`, `dalamNegeri`

## Kolom yang Dihapus (Preprocessing)

Kolom enrichment pihak ketiga (bukan data resmi SIRUP): `potensiPemborosan`, `tags.isInappropriate`, dll.

## Data Pendukung

| File | Sumber | Lisensi |
|------|--------|---------|
| `kabkota.geojson` | [eppofahmi/geojson-indonesia](https://github.com/eppofahmi/geojson-indonesia) | Open |
| `geo/kabkota_clean.geojson` | Derived (514 features) | — |

## Cara Reproduksi

1. Unduh/export data SIRUP sesuai akses LKPP
2. Simpan sebagai `data/year-2026_merged.csv`
3. Jalankan `python run_pipeline.py`

## Integritas

```powershell
python 05_validate.py
# atau
curl http://127.0.0.1:8000/api/meta
```

Expected: `"total_rows": 3002992`, `"integrity": "full"`

## Etika Penggunaan Data

- Data publik untuk transparansi pengadaan
- RPI **bukan** kesimpulan hukum — alat prioritas audit
- Tidak menampilkan data pribadi individu (hanya entitas institusi)

## Sitasi untuk Esai (contoh)

> Lembaga Kebijakan Pengadaan Barang/Jasa Pemerintah. (2026). *Sistem Informasi Rencana Umum Pengadaan (SIRUP)*. Diakses dari https://sirup.lkpp.go.id/

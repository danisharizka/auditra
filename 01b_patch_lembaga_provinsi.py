"""
Auditra - Patch: Hapus baris dengan lembaga = nama provinsi murni
Data quality issue dari SIRUP: sebagian baris kolom 'lembaga' keisi nama
provinsi polos (bukan nama instansi), sehingga mencemari dropdown filter
'Lembaga' di dashboard dengan entri yang seharusnya cuma ada di filter
'Provinsi'.

Jalankan SETELAH 01_cleaning.py tapi SEBELUM 02_scoring.py jika kamu sudah
punya data_clean.csv dari run sebelumnya dan tidak mau cleaning ulang dari awal.

Bisa juga dijalankan di tahap manapun (data_scored.csv, data_network.csv)
karena hanya filter baris, tidak mengubah kolom.
"""

import pandas as pd

INPUT_PATH  = 'data/data_clean.csv'    # ganti ke tahap data yang mau dipatch
OUTPUT_PATH = 'data/data_clean.csv'    # overwrite in-place, atau ganti nama baru

LIST_PROVINSI = {
    'aceh','sumatera utara','sumatera barat','riau','jambi','sumatera selatan',
    'bengkulu','lampung','kepulauan bangka belitung','kepulauan riau','dki jakarta',
    'jawa barat','jawa tengah','di yogyakarta','daerah istimewa yogyakarta','jawa timur',
    'banten','bali','nusa tenggara barat','nusa tenggara timur','kalimantan barat',
    'kalimantan tengah','kalimantan selatan','kalimantan timur','kalimantan utara',
    'sulawesi utara','sulawesi tengah','sulawesi selatan','sulawesi tenggara','gorontalo',
    'sulawesi barat','maluku','maluku utara','papua','papua barat','papua tengah',
    'papua pegunungan','papua selatan','papua barat daya',
}

print("Loading data...")
df = pd.read_csv(INPUT_PATH, low_memory=False)
print(f"  Shape sebelum: {df.shape}")

mask = df['lembaga'].astype(str).str.strip().str.lower().isin(LIST_PROVINSI)
n_affected = mask.sum()

print(f"\nBaris dengan lembaga = nama provinsi murni: {n_affected}")
if n_affected > 0:
    print("Contoh lembaga yang ditemukan (akan dihapus):")
    print(df.loc[mask, 'lembaga'].value_counts().to_string())

df_clean = df[~mask].copy()
print(f"\n  Shape sesudah: {df_clean.shape}")

df_clean.to_csv(OUTPUT_PATH, index=False)
print(f"\n✓ Saved → {OUTPUT_PATH}")

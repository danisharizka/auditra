import math
import os
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "output" / "data_network.parquet"
OUTPUT_DIR = ROOT / "output" / "chunks"

def export_chunks(chunks_count: int = 10):
    """
    Split the massive parquet dataset into smaller chunks (< 25MB).
    This allows deployment via GitHub without hitting the 100MB file size limit.
    """
    if not INPUT_FILE.exists():
        print(f"File not found: {INPUT_FILE}")
        return

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_parquet(INPUT_FILE)
    total_rows = len(df)
    chunk_size = math.ceil(total_rows / chunks_count)

    print(f"Splitting into {chunks_count} chunks of ~{chunk_size} rows each...")
    for i in range(chunks_count):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total_rows)
        chunk = df.iloc[start:end]
        out_file = OUTPUT_DIR / f"part_{i}.parquet"
        
        # Save chunk
        chunk.to_parquet(out_file, index=False, compression="zstd")
        size_mb = os.path.getsize(out_file) / 1e6
        print(f"Saved {out_file.name} (rows {start} to {end}) - {size_mb:.2f} MB")

    print("\nData chunking complete! The output/chunks directory is tracked in git.")
    print("Railway deployment will auto-assemble these chunks using DuckDB.")

if __name__ == "__main__":
    export_chunks()

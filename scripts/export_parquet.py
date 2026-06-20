"""
Convert data_network.csv → parquet (same rows/columns, faster queries).
Run after 03_network_analysis.py.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "output" / "data_network.csv"
PARQUET = ROOT / "output" / "data_network.parquet"


def main() -> None:
    if not CSV.exists():
        raise SystemExit(f"Missing {CSV} — run pipeline first.")

    con = duckdb.connect()
    before = con.execute(
        f"SELECT COUNT(*) FROM read_csv_auto('{CSV.as_posix()}', header=true)"
    ).fetchone()[0]

    con.execute(
        f"""
        COPY (SELECT * FROM read_csv_auto('{CSV.as_posix()}', header=true))
        TO '{PARQUET.as_posix()}' (FORMAT PARQUET)
        """
    )

    after = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PARQUET.as_posix()}')"
    ).fetchone()[0]

    print(f"Rows before: {before:,}")
    print(f"Rows after : {after:,}")
    if before != after:
        raise SystemExit("INTEGRITY ERROR: row count mismatch!")
    print(f"✓ Saved → {PARQUET}")


if __name__ == "__main__":
    main()

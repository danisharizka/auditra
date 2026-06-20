"""
Auditra — Pipeline Orchestrator
Menjalankan seluruh lifecycle: EDA → cleaning → scoring → network → geo → validation.

Usage:
  python run_pipeline.py              # full pipeline
  python run_pipeline.py --from 02    # mulai dari step 02_scoring
  python run_pipeline.py --skip-eda   # lewati EDA
  python run_pipeline.py --validate-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("00", "00_eda.py", "Exploratory Data Analysis"),
    ("01", "01_cleaning.py", "Data Cleaning"),
    ("01b", "01b_patch_lembaga_provinsi.py", "Patch Lembaga/Provinsi"),
    ("02", "02_scoring.py", "Risk Scoring (RPI)"),
    ("03", "03_network_analysis.py", "Knowledge Graph & Network"),
    ("03b", "03b_geo_matching.py", "Geo Matching"),
    ("05", "05_validate.py", "Data Validation"),
    ("06", "06_sensitivity_analysis.py", "Sensitivity Analysis"),
]


def run_step(script: str, label: str) -> float:
    path = ROOT / script
    if not path.exists():
        raise FileNotFoundError(f"Script tidak ditemukan: {path}")

    print(f"\n{'='*60}")
    print(f"▶ {label} ({script})")
    print(f"{'='*60}")
    t0 = time.perf_counter()
    result = subprocess.run([sys.executable, str(path)], cwd=str(ROOT))
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        raise SystemExit(f"Gagal di {script} (exit {result.returncode})")

    print(f"✓ Selesai dalam {elapsed:.1f}s")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditra pipeline orchestrator")
    parser.add_argument("--from", dest="from_step", default="00", help="Mulai dari step (00, 01, 02, …)")
    parser.add_argument("--skip-eda", action="store_true", help="Lewati 00_eda.py")
    parser.add_argument("--validate-only", action="store_true", help="Hanya jalankan 05_validate.py")
    args = parser.parse_args()

    if args.validate_only:
        run_step("05_validate.py", "Data Validation")
        return

    start_idx = next((i for i, (code, _, _) in enumerate(STEPS) if code == args.from_step), 0)
    if args.skip_eda and start_idx == 0:
        start_idx = 1

    print("AUDITRA PIPELINE")
    print(f"Steps: {', '.join(s[0] for s in STEPS[start_idx:])}")

    total = 0.0
    for code, script, label in STEPS[start_idx:]:
        total += run_step(script, label)

    print(f"\n{'='*60}")
    print(f"✓ Pipeline selesai — total {total:.1f}s ({total/60:.1f} menit)")
    print(f"{'='*60}")
    print("\nLangkah deploy web:")
    print("  pip install -r requirements-web.txt")
    print("  uvicorn api.main:app --reload --port 8000")
    print("  cd web && npm run dev")


if __name__ == "__main__":
    main()

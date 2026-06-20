"""
Auditra - Step 5: Data Validation
Validasi kualitas data di setiap tahap pipeline.

Output:
  output/reports/validation_report.txt
"""

from __future__ import annotations

from pipeline.config import reports_dir
from pipeline.validate import run_all_validations


def main() -> None:
    print("=" * 60)
    print("AUDITRA — DATA VALIDATION")
    print("=" * 60)

    results = run_all_validations()
    lines = []
    all_pass = True

    for r in results:
        print(r.summary())
        print()
        lines.append(r.summary())
        lines.append("")
        if not r.passed:
            all_pass = False

    out = reports_dir() / "validation_report.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Report → {out}")

    if not all_pass:
        raise SystemExit(1)
    print("\n✓ Semua validasi PASS")


if __name__ == "__main__":
    main()

"""
Auditra - Step 0: Exploratory Data Analysis (EDA)
Analisis eksploratif data mentah SIRUP sebelum preprocessing.

Output:
  output/reports/eda_report.md   — ringkasan teks
  output/reports/eda_stats.json  — statistik terstruktur
  output/reports/eda_charts.html — visualisasi interaktif (Plotly)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pipeline.config import load_config, reports_dir

SIRUP_COLS = [
    "id", "paket", "jenisPengadaan", "metode", "lembaga", "satker",
    "lokasi", "pagu", "pemilihanDate", "sumberDana", "isUMKM",
    "volumePekerjaan", "uraianPekerjaan", "spesifikasiPekerjaan",
    "ownerType", "dalamNegeri",
]


def iqr_outliers(series: pd.Series) -> dict:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    return {
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "lower_fence": float(lower),
        "upper_fence": float(upper),
        "n_outliers": int(mask.sum()),
        "pct_outliers": round(mask.mean() * 100, 2),
    }


def main() -> None:
    cfg = load_config()
    input_path = Path(cfg["paths"]["raw"])
    seed = cfg["eda"]["random_seed"]
    sample_n = cfg["eda"]["sample_size"]

    if not input_path.exists():
        raise FileNotFoundError(f"Data mentah tidak ditemukan: {input_path}")

    print("=" * 60)
    print("AUDITRA — EXPLORATORY DATA ANALYSIS")
    print("=" * 60)
    print(f"Input : {input_path}")
    print(f"Sample: {sample_n:,} baris (seed={seed}) untuk visualisasi")

    t0 = datetime.now(timezone.utc)
    df_full = pd.read_csv(input_path, low_memory=False)
    n_rows, n_cols = df_full.shape

    # ── Profil dataset ────────────────────────────────────────────────
    dtypes = {c: str(t) for c, t in df_full.dtypes.items()}
    null_counts = df_full.isnull().sum()
    null_pct = (null_counts / n_rows * 100).round(2)
    null_report = {
        c: {"count": int(null_counts[c]), "pct": float(null_pct[c])}
        for c in null_counts.index if null_counts[c] > 0
    }

    dup_id = int(df_full["id"].duplicated().sum()) if "id" in df_full.columns else -1
    pagu_stats = df_full["pagu"].describe().to_dict() if "pagu" in df_full.columns else {}
    pagu_outliers = iqr_outliers(df_full["pagu"].dropna()) if "pagu" in df_full.columns else {}

    cat_cols = ["metode", "jenisPengadaan", "lembaga", "sumberDana"]
    distributions = {}
    for col in cat_cols:
        if col in df_full.columns:
            vc = df_full[col].value_counts().head(15)
            distributions[col] = {str(k): int(v) for k, v in vc.items()}

    # ── Sample untuk chart ────────────────────────────────────────────
    df = df_full.sample(n=min(sample_n, n_rows), random_state=seed)

    stats = {
        "generated_at": t0.isoformat(),
        "input_file": str(input_path),
        "shape": {"rows": n_rows, "columns": n_cols},
        "dtypes": dtypes,
        "null_report": null_report,
        "duplicate_id": dup_id,
        "pagu": {
            "describe": {k: float(v) if isinstance(v, (np.floating, float)) else v for k, v in pagu_stats.items()},
            "outliers_iqr": pagu_outliers,
            "zero_or_negative": int((df_full["pagu"] <= 0).sum()) if "pagu" in df_full.columns else None,
        },
        "distributions_top15": distributions,
        "unique_counts": {
            col: int(df_full[col].nunique())
            for col in ["lembaga", "satker", "lokasi", "metode"]
            if col in df_full.columns
        },
    }

    # ── Markdown report ───────────────────────────────────────────────
    lines = [
        "# Auditra — EDA Report",
        "",
        f"**Generated:** {t0.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Source:** `{input_path}`",
        "",
        "## 1. Dimensi Dataset",
        f"- Baris: **{n_rows:,}**",
        f"- Kolom: **{n_cols}**",
        f"- Duplikat `id`: **{dup_id:,}**",
        "",
        "## 2. Missing Values",
    ]
    if null_report:
        lines.append("| Kolom | Null | % |")
        lines.append("|-------|------|---|")
        for col, info in sorted(null_report.items(), key=lambda x: -x[1]["count"]):
            lines.append(f"| {col} | {info['count']:,} | {info['pct']}% |")
    else:
        lines.append("_Tidak ada null value._")

    lines += [
        "",
        "## 3. Statistik Pagu",
        f"- Mean: Rp {pagu_stats.get('mean', 0):,.0f}",
        f"- Median: Rp {pagu_stats.get('50%', 0):,.0f}",
        f"- Max: Rp {pagu_stats.get('max', 0):,.0f}",
        f"- Pagu ≤ 0: {stats['pagu']['zero_or_negative']:,} baris",
        f"- Outlier (IQR): {pagu_outliers.get('n_outliers', 0):,} ({pagu_outliers.get('pct_outliers', 0)}%)",
        "",
        "## 4. Kardinalitas",
    ]
    for col, n in stats["unique_counts"].items():
        lines.append(f"- `{col}`: {n:,} unik")

    lines += ["", "## 5. Distribusi Kategorikal (Top)", ""]
    for col, dist in distributions.items():
        lines.append(f"### {col}")
        for k, v in list(dist.items())[:8]:
            lines.append(f"- {k}: {v:,}")
        lines.append("")

    lines += [
        "## 6. Rekomendasi Preprocessing",
        "- Hapus kolom enrichment Nemesis (bukan data SIRUP murni)",
        "- Drop duplikat `id`",
        "- Filter `pagu > 0`",
        "- Normalisasi whitespace & kategori `sumberDana`",
        "- Patch baris `lembaga` = nama provinsi polos",
        "",
        "---",
        "_Jalankan `01_cleaning.py` untuk preprocessing._",
    ]

    out_dir = reports_dir()
    report_md = out_dir / "eda_report.md"
    report_json = out_dir / "eda_stats.json"
    report_html = out_dir / "eda_charts.html"

    report_md.write_text("\n".join(lines), encoding="utf-8")
    report_json.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Plotly charts ─────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Distribusi Pagu (log)", "Metode Pengadaan", "Jenis Pengadaan", "Pagu vs Metode (box)"),
        specs=[[{"type": "histogram"}, {"type": "bar"}], [{"type": "bar"}, {"type": "box"}]],
    )

    if "pagu" in df.columns:
        fig.add_trace(
            go.Histogram(x=np.log1p(df["pagu"]), nbinsx=50, name="log(pagu)"),
            row=1, col=1,
        )

    if "metode" in df.columns:
        vc = df["metode"].value_counts().head(10)
        fig.add_trace(go.Bar(x=vc.index, y=vc.values, name="metode"), row=1, col=2)

    if "jenisPengadaan" in df.columns:
        vc = df["jenisPengadaan"].value_counts().head(10)
        fig.add_trace(go.Bar(x=vc.index, y=vc.values, name="jenis"), row=2, col=1)

    if "pagu" in df.columns and "metode" in df.columns:
        for metode in df["metode"].value_counts().head(5).index:
            subset = df[df["metode"] == metode]["pagu"]
            fig.add_trace(
                go.Box(y=np.log1p(subset), name=str(metode), showlegend=False),
                row=2, col=2,
            )

    fig.update_layout(
        title="Auditra EDA — Sample Visualizations",
        height=700,
        showlegend=False,
        template="plotly_white",
    )
    fig.write_html(str(report_html))

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\nBaris     : {n_rows:,}")
    print(f"Duplikat  : {dup_id:,}")
    print(f"Null cols : {len(null_report)}")
    print(f"Pagu ≤ 0  : {stats['pagu']['zero_or_negative']:,}")
    print(f"\n✓ {report_md}")
    print(f"✓ {report_json}")
    print(f"✓ {report_html}")
    print(f"\nSelesai dalam {elapsed:.1f}s")


if __name__ == "__main__":
    main()

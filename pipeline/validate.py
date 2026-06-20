"""Data quality validation at each pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from pipeline.config import load_config


@dataclass
class ValidationResult:
    stage: str
    path: str
    passed: bool = True
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.checks.append(f"OK  {msg}")

    def fail(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def summary(self) -> str:
        lines = [f"=== Validation: {self.stage} ===", f"File: {self.path}"]
        lines.extend(self.checks)
        if self.errors:
            lines.append("ERRORS:")
            lines.extend(f"  - {e}" for e in self.errors)
        lines.append(f"Result: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


def _read_csv(path: Path, nrows: int | None = None) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, nrows=nrows)


def validate_raw(path: Path | None = None) -> ValidationResult:
    cfg = load_config()
    path = path or Path(cfg["paths"]["raw"])
    res = ValidationResult(stage="raw", path=str(path))

    if not path.exists():
        res.fail(f"File tidak ditemukan: {path}")
        return res

    df = _read_csv(path, nrows=5000)
    res.ok(f"Sample readable ({len(df):,} baris di-sample)")

    required = {"id", "paket", "metode", "lembaga", "pagu", "lokasi"}
    missing = required - set(df.columns)
    if missing:
        res.fail(f"Kolom wajib hilang: {sorted(missing)}")
    else:
        res.ok(f"Kolom wajib ada: {sorted(required)}")

    null_id = df["id"].isnull().sum() if "id" in df.columns else 0
    if null_id:
        res.fail(f"id null pada sample: {null_id}")
    else:
        res.ok("id tidak null (sample)")

    return res


def validate_clean(path: Path | None = None) -> ValidationResult:
    cfg = load_config()
    path = path or Path(cfg["paths"]["clean"])
    min_rows = cfg["validation"]["min_rows"]
    res = ValidationResult(stage="clean", path=str(path))

    if not path.exists():
        res.fail(f"File tidak ditemukan: {path}")
        return res

    df = _read_csv(path)
    res.ok(f"Shape: {df.shape[0]:,} baris × {df.shape[1]} kolom")

    if len(df) < min_rows:
        res.fail(f"Baris terlalu sedikit: {len(df)} < {min_rows}")
    else:
        res.ok(f"Row count ≥ {min_rows:,}")

    dup = df["id"].duplicated().sum()
    if dup:
        res.fail(f"Duplikat id: {dup}")
    else:
        res.ok("Tidak ada duplikat id")

    bad_pagu = (df["pagu"] <= 0).sum()
    if bad_pagu:
        res.fail(f"Pagu ≤ 0: {bad_pagu} baris")
    else:
        res.ok("Semua pagu > 0")

    null_cols = df.isnull().sum()
    null_cols = null_cols[null_cols > 0]
    if len(null_cols):
        res.ok(f"Null columns (expected): {null_cols.to_dict()}")
    else:
        res.ok("Tidak ada null")

    return res


def validate_scored(path: Path | None = None) -> ValidationResult:
    cfg = load_config()
    path = path or Path(cfg["paths"]["scored"])
    vcfg = cfg["validation"]
    res = ValidationResult(stage="scored", path=str(path))

    if not path.exists():
        res.fail(f"File tidak ditemukan: {path}")
        return res

    df = _read_csv(path)
    res.ok(f"Shape: {df.shape[0]:,} baris")

    signal_cols = [c for c in df.columns if c.startswith("s") and "_" in c[:4]]
    for col in ["s1_metode", "s2_pagu_anomali", "RPI", "risk_label"]:
        if col not in df.columns:
            res.fail(f"Kolom hilang: {col}")
        else:
            res.ok(f"Kolom {col} ada")

    if "RPI" in df.columns:
        rpi = df["RPI"]
        if rpi.min() < vcfg["rpi_min"] or rpi.max() > vcfg["rpi_max"]:
            res.fail(f"RPI di luar [{vcfg['rpi_min']}, {vcfg['rpi_max']}]: min={rpi.min()}, max={rpi.max()}")
        else:
            res.ok(f"RPI dalam rentang 0–100 (mean={rpi.mean():.2f})")

    if "risk_label" in df.columns:
        valid = set(vcfg["valid_risk_labels"])
        invalid = set(df["risk_label"].unique()) - valid
        if invalid:
            res.fail(f"risk_label tidak valid: {invalid}")
        else:
            dist = df["risk_label"].value_counts().to_dict()
            res.ok(f"Distribusi risk_label: {dist}")

    for col in signal_cols:
        if col in df.columns:
            if df[col].min() < -0.01 or df[col].max() > 1.01:
                res.fail(f"{col} di luar [0,1]: min={df[col].min()}, max={df[col].max()}")

    return res


def validate_network(path: Path | None = None) -> ValidationResult:
    cfg = load_config()
    path = path or Path(cfg["paths"]["network"])
    res = ValidationResult(stage="network", path=str(path))

    if not path.exists():
        res.fail(f"File tidak ditemukan: {path}")
        return res

    df = _read_csv(path)
    res.ok(f"Shape: {df.shape[0]:,} baris × {df.shape[1]} kolom")

    kg_cols = ["kg_pagerank", "kg_risk_influence", "kg_betweenness"]
    present = [c for c in kg_cols if c in df.columns]
    if len(present) < 2:
        res.fail(f"Kolom KG metrics kurang: {kg_cols}")
    else:
        res.ok(f"KG metrics: {present}")

    scored_path = Path(cfg["paths"]["scored"])
    if scored_path.exists():
        n_scored = len(_read_csv(scored_path, nrows=None))
        if len(df) != n_scored:
            res.fail(f"Row count mismatch vs scored: {len(df)} vs {n_scored}")
        else:
            res.ok(f"Row count match scored: {len(df):,}")

    return res


def validate_geo(lookup_path: Path | None = None) -> ValidationResult:
    cfg = load_config()
    path = lookup_path or Path(cfg["paths"]["geo_lookup"])
    res = ValidationResult(stage="geo", path=str(path))

    if not path.exists():
        res.fail(f"File tidak ditemukan: {path}")
        return res

    df = _read_csv(path)
    res.ok(f"Lookup entries: {len(df):,}")

    for col in ["lokasi_sirup", "kabkot_id", "kabkot_name", "prov_name"]:
        if col not in df.columns:
            res.fail(f"Kolom hilang: {col}")
        else:
            res.ok(f"Kolom {col} ada")

    unmatched_path = Path(cfg["paths"]["geo_lookup"]).parent / "unmatched_report.txt"
    if unmatched_path.exists():
        n_unmatched = unmatched_path.read_text(encoding="utf-8").count("→")
        res.ok(f"Lokasi edge case (unmatched report): {n_unmatched} entri — lihat geo/unmatched_report.txt")
    else:
        res.ok("Tidak ada unmatched report")

    if "match_type" in df.columns:
        fuzzy = (df["match_type"] == "fuzzy").sum()
        cross = (df["match_type"] == "cross_province_exact").sum()
        exact = (df["match_type"] == "exact").sum()
        res.ok(f"Match quality: exact={exact:,}, fuzzy={fuzzy:,}, cross_province={cross:,}")
        if cross > 0:
            res.ok(f"Cross-province match: {cross} (lokasi multi-wilayah — limitasi dokumentasi)")

    return res


def run_all_validations() -> list[ValidationResult]:
    cfg = load_config()
    results = [
        validate_raw(Path(cfg["paths"]["raw"])),
        validate_clean(),
        validate_scored(),
        validate_network(),
        validate_geo(),
    ]
    return results

"""Unit tests for pipeline validation."""

from pathlib import Path

import pandas as pd
import pytest

from pipeline.validate import ValidationResult, validate_clean, validate_scored


@pytest.fixture
def tmp_clean_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "paket": ["A", "B", "C"],
        "metode": ["Tender", "Tender", "Tender"],
        "lembaga": ["K1", "K2", "K3"],
        "pagu": [100_000_000, 200_000_000, 300_000_000],
        "lokasi": ["Jakarta", "Bandung", "Surabaya"],
    })
    path = tmp_path / "clean.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def tmp_scored_csv(tmp_path: Path) -> Path:
    df = pd.DataFrame({
        "id": [1, 2],
        "RPI": [45.5, 72.0],
        "risk_label": ["SEDANG", "KRITIS"],
        "s1_metode": [0.05, 1.0],
        "s2_pagu_anomali": [0.3, 0.8],
        "s3_fragmentasi": [0.0, 0.5],
        "s4_konsentrasi": [0.1, 0.9],
        "s5_umkm": [0.0, 0.0],
        "s6_dana_metode": [0.0, 1.0],
        "s7_reputasi": [0.2, 0.7],
    })
    path = tmp_path / "scored.csv"
    df.to_csv(path, index=False)
    return path


def test_validate_clean_passes(tmp_clean_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _cfg() -> dict:
        return {"validation": {"min_rows": 1}, "paths": {"clean": str(tmp_clean_csv)}}

    monkeypatch.setattr("pipeline.validate.load_config", _cfg)
    result = validate_clean(tmp_clean_csv)
    assert result.passed
    assert "Tidak ada duplikat id" in "\n".join(result.checks)


def test_validate_clean_fails_on_duplicate(tmp_path: Path) -> None:
    df = pd.DataFrame({"id": [1, 1], "pagu": [100, 200]})
    path = tmp_path / "bad.csv"
    df.to_csv(path, index=False)
    result = validate_clean(path)
    assert not result.passed


def test_validate_scored_passes(tmp_scored_csv: Path) -> None:
    result = validate_scored(tmp_scored_csv)
    assert result.passed


def test_validation_result_summary() -> None:
    r = ValidationResult(stage="test", path="/tmp/x.csv")
    r.ok("check 1")
    r.fail("error 1")
    assert not r.passed
    assert "FAIL" in r.summary()

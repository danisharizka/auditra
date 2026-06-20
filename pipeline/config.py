"""Load central pipeline configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "pipeline.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path_key: str) -> Path:
    cfg = load_config()
    return ROOT / cfg["paths"][path_key]


def reports_dir() -> Path:
    cfg = load_config()
    d = ROOT / cfg["paths"]["reports_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d

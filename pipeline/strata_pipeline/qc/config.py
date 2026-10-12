"""Loads `pipeline/strata_pipeline/config.yaml`'s `qc:` block — docs/07_DATA_AND_ALGORITHMS.md §3
says thresholds live there, never hard-coded in a rule module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_qc_config() -> dict[str, Any]:
    raw: dict[str, Any] = yaml.safe_load(_CONFIG_PATH.read_text())
    qc_cfg: dict[str, Any] = raw["qc"]
    return qc_cfg

"""Loads `recon/ddr_codes.yaml` — the single source of truth for raw DDR activity-code
normalization, shared by `ingest/ddr.py` and `recon/reconciliation.py` (docs/07 §7)."""

from __future__ import annotations

from pathlib import Path

import yaml

_PATH = Path(__file__).parent / "ddr_codes.yaml"
_OTHER = "OTHER"


def load_ddr_code_rules() -> list[tuple[str, str]]:
    raw: dict[str, list[list[str]]] = yaml.safe_load(_PATH.read_text())
    return [(prefix, normalized) for prefix, normalized in raw["rules"]]


def normalize_code(raw_code: str, rules: list[tuple[str, str]]) -> str:
    code = raw_code.strip().lower()
    for prefix, normalized in rules:
        if code.startswith(prefix):
            return normalized
    return _OTHER

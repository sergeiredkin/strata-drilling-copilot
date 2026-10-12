"""Live-mode settings — docs/03_ARCHITECTURE.md §2: the API never recomputes analytics on
request, it only serves `data/export/**` (the same tree `apps/web/public/data` is copied from),
so static mode and live mode show identical numbers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_DIR = _REPO_ROOT / "apps" / "web" / "public" / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    cors_origins: list[str]


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("STRATA_DATA_DIR", str(_DEFAULT_DATA_DIR)))
    origins_raw = os.environ.get("STRATA_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
    cors_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
    return Settings(data_dir=data_dir, cors_origins=cors_origins)

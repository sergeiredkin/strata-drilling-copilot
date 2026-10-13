"""Shared FastAPI dependencies: one `Settings` instance per process, plus the id-shaped
path/query parameter type every route must use for anything joined onto `settings.data_dir` —
see `SAFE_ID_PATTERN`'s docstring for why."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Path, Query

from .settings import Settings, load_settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

# Deliberately stricter than contracts.WellId's own regex (`^[A-Za-z0-9_\-().]+$`): that pattern
# allows `.` for generality, which means the literal value `..` itself satisfies it — tried and
# confirmed live (`GET /wells/%2e%2e/sections` still read `wells/../sections.json` with that
# pattern). No real id in this codebase (well, evidence, issue) ever contains a `.` or `(`/`)`,
# so this excludes them entirely rather than trying to out-think every traversal sequence a more
# permissive charset could form. Found via a security review:
# docs/audits/2026-10-13_STRATA_ENGINEERING_AUDIT.md P1-15 — confirmed a real, if low-impact
# today, directory-escape primitive on every `{well_id}`/`{issue_id}`/`?well=` parameter that
# was a plain unvalidated `str`.
SAFE_ID_PATTERN = r"^[A-Za-z0-9_-]+$"

SafeIdPath = Annotated[str, Path(pattern=SAFE_ID_PATTERN)]
SafeIdQuery = Annotated[str | None, Query(pattern=SAFE_ID_PATTERN)]

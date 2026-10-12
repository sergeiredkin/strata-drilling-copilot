"""Shared FastAPI dependency: one `Settings` instance per process, injected into every route."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .settings import Settings, load_settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

"""Contract tests run against the repo's own committed fixture export
(`apps/web/public/data`) — real, schema-valid data already used by static mode, so a passing
test here means live mode would serve byte-for-byte the same shapes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from strata_api.deps import get_settings
from strata_api.main import app
from strata_api.settings import Settings

FIXTURE_DATA_DIR = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "data"


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=FIXTURE_DATA_DIR, cors_origins=["http://localhost:5173"]
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

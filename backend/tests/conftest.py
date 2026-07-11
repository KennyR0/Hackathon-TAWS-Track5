from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.contracts.api import build_openapi_document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OPENAPI_SNAPSHOT = REPO_ROOT / "contracts" / "openapi.json"
CONSUMER_FIELDS = REPO_ROOT / "contracts" / "consumer-fields.json"


@pytest.fixture(scope="session")
def openapi_document() -> dict[str, object]:
    return build_openapi_document()


@pytest.fixture(scope="session")
def consumer_manifest() -> dict[str, object]:
    return json.loads(CONSUMER_FIELDS.read_text(encoding="utf-8"))

import sys
import tomllib
import tomli_w
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module
from app import app

BASE = Path(__file__).parent.parent

MINIMAL_CV = {
    "lang": "da",
    "personal": {
        "name": "Test Testesen",
        "title": "Udvikler",
        "email": "test@example.com",
        "phone": "12345678",
        "address": "Testvej 1",
        "photo": "",
    },
    "summary": {"text": "Testopsummering"},
    "about": {"text": "Om mig"},
    "languages": [],
    "skills": {"tags": []},
    "experience": [],
    "education": [],
}


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def test_version():
    """Opretter en midlertidig version-TOML i versions/da/ og rydder op bagefter."""
    versions_dir = BASE / "versions" / "da"
    versions_dir.mkdir(parents=True, exist_ok=True)
    path = versions_dir / "2099-01-01_pytest-test.toml"
    data = {**MINIMAL_CV, "_job": "Testjob", "_note": "Testnote", "_application": ""}
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
    yield path
    if path.exists():
        path.unlink()

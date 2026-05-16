"""
Unit tests — tester funktioner i isolation uden HTTP-lag.
"""
import tomli_w
import pytest
from pathlib import Path

import app as app_module
from app import list_versions


@pytest.fixture
def versions_dir(tmp_path, monkeypatch):
    """Peger app.BASE mod en midlertidig mappe så list_versions læser derfra."""
    monkeypatch.setattr(app_module, "BASE", tmp_path)
    da_dir = tmp_path / "versions" / "da"
    da_dir.mkdir(parents=True)
    return da_dir


def write_version(directory: Path, filename: str, data: dict):
    with open(directory / filename, "wb") as f:
        tomli_w.dump(data, f)


class TestListVersions:
    def test_tom_mappe_returnerer_tom_liste(self, versions_dir):
        assert list_versions("da") == []

    def test_version_uden_application_har_tomt_felt(self, versions_dir):
        write_version(versions_dir, "2099-01-01_test.toml", {
            "_job": "Testjob", "_note": "En note",
        })
        result = list_versions("da")
        assert len(result) == 1
        assert result[0]["application"] == ""

    def test_version_med_application(self, versions_dir):
        write_version(versions_dir, "2099-01-01_test.toml", {
            "_job": "Testjob", "_application": "Min ansøgning",
        })
        result = list_versions("da")
        assert result[0]["application"] == "Min ansøgning"

    def test_dato_udlaeses_fra_filnavn(self, versions_dir):
        write_version(versions_dir, "2099-06-15_et-job.toml", {"_job": "Et job"})
        result = list_versions("da")
        assert result[0]["date"] == "2099-06-15"

    def test_kladde_vises_foerst(self, versions_dir):
        write_version(versions_dir, "2099-01-01_regulaer.toml", {"_job": "Regulær"})
        write_version(versions_dir, "kladde.toml", {"_job": "Kladde"})
        result = list_versions("da")
        assert result[0]["is_kladde"] is True
        assert result[1]["is_kladde"] is False

    def test_sorterer_versioner_nyeste_foerst(self, versions_dir):
        write_version(versions_dir, "2099-01-01_gammel.toml", {"_job": "Gammel"})
        write_version(versions_dir, "2099-06-01_ny.toml", {"_job": "Ny"})
        result = list_versions("da")
        assert result[0]["date"] == "2099-06-01"
        assert result[1]["date"] == "2099-01-01"

    def test_ugyldig_toml_springes_over(self, versions_dir):
        (versions_dir / "2099-01-01_korrupt.toml").write_text("dette er ikke toml ][")
        write_version(versions_dir, "2099-02-01_god.toml", {"_job": "God fil"})
        result = list_versions("da")
        assert len(result) == 1
        assert result[0]["job"] == "God fil"

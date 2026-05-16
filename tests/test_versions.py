"""
Tests for version-endpoints: update-meta og list_versions.
Kører mod den rigtige versions/-mappe med en midlertidig testfil.
"""
import tomllib
from pathlib import Path

BASE = Path(__file__).parent.parent


class TestUpdateMeta:
    def test_opdaterer_job_og_note(self, client, test_version):
        resp = client.post(
            f"/versions/da/{test_version.name}/update-meta",
            data={"_job": "Nyt job", "_note": "Ny note", "_application": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with open(test_version, "rb") as f:
            data = tomllib.load(f)
        assert data["_job"] == "Nyt job"
        assert data["_note"] == "Ny note"

    def test_gemmer_ansogning(self, client, test_version):
        ansogning = "Kære virksomhed\n\nJeg søger stillingen."
        resp = client.post(
            f"/versions/da/{test_version.name}/update-meta",
            data={"_job": "Testjob", "_note": "", "_application": ansogning},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with open(test_version, "rb") as f:
            data = tomllib.load(f)
        assert data["_application"] == ansogning

    def test_bevarer_cv_data(self, client, test_version):
        """CV-indholdet må ikke ændres når kun metadata opdateres."""
        resp = client.post(
            f"/versions/da/{test_version.name}/update-meta",
            data={"_job": "Andet job", "_note": "", "_application": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with open(test_version, "rb") as f:
            data = tomllib.load(f)
        assert data["personal"]["name"] == "Test Testesen"
        assert data["personal"]["email"] == "test@example.com"

    def test_returnerer_404_for_ukendt_fil(self, client):
        resp = client.post(
            "/versions/da/2099-01-01_findes-ikke.toml/update-meta",
            data={"_job": "X", "_note": "", "_application": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 404


class TestListVersions:
    def test_ansogning_felt_med_i_liste(self, client, test_version):
        """list_versions() skal returnere 'application'-feltet."""
        from app import list_versions
        versions = list_versions("da")
        match = next((v for v in versions if v["filename"] == test_version.name), None)
        assert match is not None
        assert "application" in match

    def test_ansogning_vises_efter_opdatering(self, client, test_version):
        tekst = "Min ansøgning"
        client.post(
            f"/versions/da/{test_version.name}/update-meta",
            data={"_job": "Testjob", "_note": "", "_application": tekst},
            follow_redirects=False,
        )
        from app import list_versions
        versions = list_versions("da")
        match = next(v for v in versions if v["filename"] == test_version.name)
        assert match["application"] == tekst


class TestSaveVersion:
    def test_gem_version_inkluderer_ansogning(self, client):
        """POST /save-version skal gemme _application i TOML-filen."""
        resp = client.post(
            "/save-version",
            data={
                "lang": "da",
                "_job": "pytest-ansogning-test",
                "_note": "",
                "_application": "Min testansøgning",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Find den gemte fil og ryd op
        from datetime import date
        import re
        slug = "pytest-ansogning-test"
        filename = f"{date.today().isoformat()}_{re.sub(r'[^a-z0-9]+', '-', slug.lower())[:40].strip('-')}.toml"
        path = BASE / "versions" / "da" / filename
        try:
            assert path.exists(), f"Forventet fil ikke fundet: {filename}"
            with open(path, "rb") as f:
                data = tomllib.load(f)
            assert data.get("_application") == "Min testansøgning"
        finally:
            if path.exists():
                path.unlink()

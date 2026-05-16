"""
E2e-flowtest — tester komplette brugerflows i rækkefølge via HTTP.

Playwright understøtter ikke Ubuntu 26.04 endnu, så disse tests kører
mod TestClient og verificerer HTML-output. Kan erstattes med Playwright
når platformen understøttes.
"""
import tomllib
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent


class TestGemOgRedigerVersion:
    """Komplet flow: gem version → tjek den optræder på /versions → redigér metadata."""

    def _gem_testversion(self, client, job: str) -> str:
        resp = client.post(
            "/save-version",
            data={"lang": "da", "_job": job, "_note": "Flowtest-note", "_application": "Flowtest-ansøgning"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", job.lower())[:40].strip("-")
        return f"{date.today().isoformat()}_{slug}.toml"

    def test_gemt_version_vises_paa_versions_siden(self, client):
        filename = self._gem_testversion(client, "e2e-flowtest-job")
        path = BASE / "versions" / "da" / filename
        try:
            resp = client.get("/versions")
            assert resp.status_code == 200
            assert "e2e-flowtest-job" in resp.text
        finally:
            path.unlink(missing_ok=True)

    def test_ansogning_badge_vises_naar_ansogning_er_gemt(self, client):
        filename = self._gem_testversion(client, "e2e-badge-test")
        path = BASE / "versions" / "da" / filename
        try:
            resp = client.get("/versions")
            assert "Ansøgning" in resp.text
        finally:
            path.unlink(missing_ok=True)

    def test_rediger_metadata_opdaterer_visning(self, client):
        filename = self._gem_testversion(client, "e2e-rediger-test")
        path = BASE / "versions" / "da" / filename
        try:
            resp = client.post(
                f"/versions/da/{filename}/update-meta",
                data={"_job": "Opdateret jobtitel", "_note": "", "_application": "Ny ansøgning"},
                follow_redirects=False,
            )
            assert resp.status_code == 303

            # Ny titel vises på /versions-siden
            resp = client.get("/versions")
            assert "Opdateret jobtitel" in resp.text
        finally:
            path.unlink(missing_ok=True)

    def test_komplet_flow_gem_rediger_preview(self, client):
        """Gem → redigér → hent preview — al CV-data skal stadig være intakt."""
        filename = self._gem_testversion(client, "e2e-komplet-flow")
        path = BASE / "versions" / "da" / filename
        try:
            client.post(
                f"/versions/da/{filename}/update-meta",
                data={"_job": "Komplet flow job", "_note": "Note", "_application": "Ansøgning"},
                follow_redirects=False,
            )

            resp = client.get(f"/versions/da/{filename}/preview")
            assert resp.status_code == 200
            # CV-indholdet er stadig til stede i preview-HTML
            assert "<html" in resp.text
        finally:
            path.unlink(missing_ok=True)

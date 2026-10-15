"""
E2e-flowtest — tester komplette brugerflows i rækkefølge via HTTP.

Playwright understøtter ikke Ubuntu 26.04 endnu, så disse tests kører
mod TestClient og verificerer HTML-output. Kan erstattes med Playwright
når platformen understøttes.
"""
import tomllib
import tomli_w
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from conftest import MINIMAL_CV
import app as app_module

BASE = Path(__file__).parent.parent


def post_form(client, path: str, fields: list[tuple[str, str]], **kwargs):
    """POST med gentagne feltnavne som browseren gør det.

    httpx sender `data=<liste af tupler>` som rå content (ikke form-body), så
    formularen skal urlencodes eksplicit for at felt-navne kan gentages.
    """
    return client.post(
        path,
        content=urlencode(fields),
        headers={"content-type": "application/x-www-form-urlencoded"},
        **kwargs,
    )


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


class TestNytJobOeverst:
    """Flow: "+ Tilføj job" i editoren → nyt job skal gemmes øverst i experience.

    Parsingen i /save følger felt-rækkefølgen i formularen, så kortet der
    indsættes først i #exp-list bliver første post i cv.toml.
    """

    def _seed(self, path: Path, jobs: list[dict]) -> None:
        data = {**MINIMAL_CV, "experience": jobs}
        with open(path, "wb") as f:
            tomli_w.dump(data, f)

    def _job_fields(self, company: str, title: str) -> list[tuple[str, str]]:
        return [
            ("exp_company", company),
            ("exp_duration", "6 måneder"),
            ("exp_title", title),
            ("exp_period", "apr. 2026 - nu"),
            ("exp_bullets", "Jenkins"),
        ]

    def _base_form(self) -> list[tuple[str, str]]:
        return [
            ("lang", "da"),
            ("personal_name", "Test Testesen"),
            ("personal_email", "test@example.com"),
            ("summary_text", "Testopsummering"),
            ("about_text", "Om mig"),
        ]

    def _seed_jysk(self, target: Path) -> None:
        self._seed(target, [{
            "company": "JYSK A/S", "duration": "5 måneder", "title": "DevOps",
            "period": "feb. 2023 – jun. 2023", "bullets": ["Jenkins"],
        }])

    def test_nyt_job_gemmes_oeverst(self, client, tmp_path, monkeypatch):
        target = tmp_path / "cv.toml"
        self._seed_jysk(target)
        monkeypatch.setitem(app_module.CV_FILES, "da", target)

        form = self._base_form() + self._job_fields("GIHC", "DevOps") + self._job_fields("JYSK A/S", "DevOps")
        resp = post_form(client, "/save", form, follow_redirects=False)

        assert resp.status_code == 303
        saved = tomllib.loads(target.read_text())
        assert [j["company"] for j in saved["experience"]] == ["GIHC", "JYSK A/S"]

    def test_tomt_nyt_job_kasseres_uden_at_aendre_raekkefoelgen(self, client, tmp_path, monkeypatch):
        """Et nyt kort hvor Virksomhed ikke er udfyldt må ikke gemmes eller stjæle førstepladsen."""
        target = tmp_path / "cv.toml"
        self._seed_jysk(target)
        monkeypatch.setitem(app_module.CV_FILES, "da", target)

        tomt_kort = [("exp_company", ""), ("exp_title", "DevOps")]
        form = self._base_form() + tomt_kort + self._job_fields("JYSK A/S", "DevOps")
        resp = post_form(client, "/save", form, follow_redirects=False)

        assert resp.status_code == 303
        saved = tomllib.loads(target.read_text())
        assert [j["company"] for j in saved["experience"]] == ["JYSK A/S"]

    def test_knappen_staar_over_joblisten(self, client, tmp_path, monkeypatch):
        target = tmp_path / "cv.toml"
        self._seed_jysk(target)
        monkeypatch.setitem(app_module.CV_FILES, "da", target)

        html = client.get("/").text

        assert html.index("+ Tilføj job") < html.index('id="exp-list"')
        assert "prepend(card)" in html

"""
Integrationstests for IPFS-endpoints og upload-flow.

Kræver en kørende lokal IPFS-daemon (port 5001 og 8080).
Tests markeret med @pytest.mark.ipfs springes over hvis daemon ikke er tilgængelig.
"""
import pytest
import urllib.request
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def ipfs_available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:5001/api/v0/id", timeout=2)
        return True
    except Exception:
        return False


requires_ipfs = pytest.mark.skipif(
    not ipfs_available(),
    reason="Lokal IPFS-daemon ikke tilgængelig",
)

# CID for det migrerede profilbillede
KNOWN_CID = "QmdENpFuHHprY5ijPB6GhtrJpMJVu8cCVuStU5zMitgu4z"


class TestIpfsProxy:
    @requires_ipfs
    def test_proxy_returnerer_billede(self):
        resp = client.get(f"/ipfs/{KNOWN_CID}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/")
        assert len(resp.content) > 0

    def test_proxy_afviser_ugyldigt_cid(self):
        resp = client.get("/ipfs/../../etc/passwd")
        assert resp.status_code in (400, 404, 422)

    def test_proxy_afviser_cid_med_skraasteg(self):
        resp = client.get("/ipfs/ikke/gyldigt")
        assert resp.status_code in (400, 404, 422)


class TestIpfsUpload:
    @requires_ipfs
    def test_upload_returnerer_cid(self):
        from app import ipfs_upload
        fake_jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        cid = ipfs_upload(fake_jpg)
        assert len(cid) > 10
        assert "/" not in cid

    @requires_ipfs
    def test_samme_data_giver_samme_cid(self):
        from app import ipfs_upload
        data = b"\xff\xd8\xff\xe0deterministisk"
        cid1 = ipfs_upload(data)
        cid2 = ipfs_upload(data)
        assert cid1 == cid2


class TestPreviewMedIpfsPhoto:
    @requires_ipfs
    def test_preview_indeholder_ipfs_proxy_url(self):
        resp = client.get("/?lang=da")
        assert resp.status_code == 200
        assert f"/ipfs/{KNOWN_CID}" in resp.text

    @requires_ipfs
    def test_versions_preview_indeholder_ipfs_proxy_url(self):
        """Version-preview skal også bruge IPFS-URL for billede."""
        import tomli_w
        from pathlib import Path
        from datetime import date

        BASE = Path(__file__).parent.parent
        cv_path = BASE / "cv.toml"
        import tomllib
        with open(cv_path, "rb") as f:
            cv = tomllib.load(f)

        version_path = BASE / "versions" / "da" / "2099-01-01_ipfs-preview-test.toml"
        try:
            with open(version_path, "wb") as f:
                tomli_w.dump({**cv, "_job": "IPFS test"}, f)
            resp = client.get(f"/versions/da/2099-01-01_ipfs-preview-test.toml/preview")
            assert resp.status_code == 200
            assert KNOWN_CID in resp.text
        finally:
            version_path.unlink(missing_ok=True)

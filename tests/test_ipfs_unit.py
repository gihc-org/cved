"""
Unit tests for IPFS-hjælpefunktioner i app.py og render.py.
Ingen netværk, ingen IPFS-daemon påkrævet.
"""
import base64
import io
import tomli_w
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from unittest.mock import patch

import app as app_module
import render as render_module
from app import _is_cid, app
from render import _is_cid as render_is_cid, _photo_data_url, _fetch_photo_bytes

client = TestClient(app)


class TestIsCid:
    def test_cid_genkendes(self):
        assert _is_cid("QmXyz123") is True
        assert _is_cid("bafybeiabc123") is True

    def test_statisk_sti_er_ikke_cid(self):
        assert _is_cid("static/photo_abc.jpg") is False

    def test_tom_streng_er_ikke_cid(self):
        assert _is_cid("") is False

    def test_sti_med_skraasteg_er_ikke_cid(self):
        assert _is_cid("some/path/file.jpg") is False


class TestFetchPhotoBytes:
    def test_henter_fra_ipfs_gateway(self):
        fake_bytes = b"\xff\xd8\xff"  # JPEG magic bytes
        mock_response = MagicMock()
        mock_response.read.return_value = fake_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("render.urllib.request.urlopen", return_value=mock_response):
            result = _fetch_photo_bytes("QmFakeCid123")

        assert result == fake_bytes

    def test_returnerer_none_ved_gateway_fejl(self):
        with patch("render.urllib.request.urlopen", side_effect=Exception("timeout")):
            result = _fetch_photo_bytes("QmFakeCid123")
        assert result is None

    def test_henter_fra_filsystem_for_gammel_sti(self, tmp_path, monkeypatch):
        monkeypatch.setattr(render_module, "BASE", tmp_path)
        photo_file = tmp_path / "static" / "photo_test.jpg"
        photo_file.parent.mkdir()
        photo_file.write_bytes(b"fakeimagedata")

        result = _fetch_photo_bytes("static/photo_test.jpg")
        assert result == b"fakeimagedata"

    def test_returnerer_none_for_manglende_fil(self, tmp_path, monkeypatch):
        monkeypatch.setattr(render_module, "BASE", tmp_path)
        result = _fetch_photo_bytes("static/findes_ikke.jpg")
        assert result is None

    def test_returnerer_none_for_tom_streng(self):
        result = _fetch_photo_bytes("")
        assert result is None


class TestPhotoDataUrl:
    def test_returnerer_data_url(self):
        fake_bytes = b"imagedata"
        with patch("render._fetch_photo_bytes", return_value=fake_bytes):
            result = _photo_data_url("QmFake")
        expected = "data:image/jpeg;base64," + base64.b64encode(fake_bytes).decode()
        assert result == expected

    def test_returnerer_tom_streng_naar_ingen_bytes(self):
        with patch("render._fetch_photo_bytes", return_value=None):
            result = _photo_data_url("QmFake")
        assert result == ""


class TestEditorPhotoCid:
    FAKE_CID = "QmFakeCid123abc"

    def _minimal_cv(self, photo):
        return {
            "lang": "da",
            "personal": {"name": "Test", "title": "Dev", "email": "t@t.dk",
                         "phone": "12345678", "address": "Testvej 1", "photo": photo},
            "summary": {"text": ""},
            "about": {"text": ""},
            "languages": [],
            "skills": {"tags": []},
            "experience": [],
            "education": [],
        }

    def test_cid_oversaettes_til_ipfs_url_i_editor(self):
        with patch("app.load_cv", return_value=self._minimal_cv(self.FAKE_CID)):
            resp = client.get("/", follow_redirects=True)
        assert resp.status_code == 200
        assert f"/ipfs/{self.FAKE_CID}" in resp.text

    def test_tom_photo_viser_ingen_ipfs_url(self):
        with patch("app.load_cv", return_value=self._minimal_cv("")):
            resp = client.get("/", follow_redirects=True)
        assert resp.status_code == 200
        assert "/ipfs/" not in resp.text

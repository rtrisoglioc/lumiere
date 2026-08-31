"""Backend tests for Pro Editor (Phase a):
- POST /api/video/jobs/{id}/edit -> creates new edit job (kind=edit) with edited_path/aspect
- GET /api/video/{new_id}/download -> 206 with Range + faststart mp4 (moov near front)
- PUT/GET /api/me/preferences persists per-user logo settings
- POST /api/me/logo + GET /api/me/logo (image/png)
- DELETE /api/video/jobs/{id}
"""
import os
import io
import struct
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_TOKEN = "admin_sess_1788155531096"
SRC_JOB = "admin-demo-vid"

pytestmark = pytest.mark.skipif(not BASE_URL, reason="REACT_APP_BACKEND_URL missing")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}"})
    return s


def _tiny_png_bytes():
    # 2x2 transparent PNG (fallback if PIL missing)
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGBA", (32, 32), (255, 0, 128, 200)).save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        return bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000020000000208060000"
            "0072B60D24000000164944415478DA6364FCCF80000000FFFF"  # not perfectly valid
            "0000FFFF03000000060005D6E56A960000000049454E44AE426082"
        )


# ---------------- LOGO upload / get ----------------
def test_me_logo_upload_and_fetch(client):
    png = _tiny_png_bytes()
    r = client.post(f"{BASE_URL}/api/me/logo",
                    files={"file": ("logo.png", png, "image/png")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True

    r2 = client.get(f"{BASE_URL}/api/me/logo?auth={ADMIN_TOKEN}")
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("image/png")
    assert len(r2.content) > 0


# ---------------- Preferences persistence ----------------
def test_preferences_persist(client):
    payload = {"logo": {"enabled": True, "x": 0.1, "y": 0.9, "scale": 0.22, "opacity": 0.75}}
    r = client.put(f"{BASE_URL}/api/me/preferences", json=payload)
    assert r.status_code == 200, r.text

    r = client.get(f"{BASE_URL}/api/me/preferences")
    assert r.status_code == 200
    d = r.json()
    assert d["has_logo"] is True
    lg = d["logo"]
    assert lg["enabled"] is True
    assert abs(lg["x"] - 0.1) < 1e-6
    assert abs(lg["y"] - 0.9) < 1e-6
    assert abs(lg["scale"] - 0.22) < 1e-6
    assert abs(lg["opacity"] - 0.75) < 1e-6


# ---------------- Edit pipeline: reframe 16:9 -> 9:16 no logo ----------------
_created_ids = []


def test_edit_reframe_9_16_no_logo(client):
    body = {"aspect": "9:16", "filter": "cinematic", "speed": 1.0,
            "logo": {"enabled": False}}
    r = client.post(f"{BASE_URL}/api/video/jobs/{SRC_JOB}/edit", json=body, timeout=300)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["kind"] == "edit"
    assert j["parent_job"] == SRC_JOB
    assert j["status"] == "DONE"
    assert j["options"]["aspect_ratio"] == "9:16"
    assert j["options"]["filter"] == "cinematic"
    assert j["edited_path"]
    assert "_id" not in j
    _created_ids.append(j["id"])


def test_edited_download_range_206(client):
    assert _created_ids, "prior test should have created an edit"
    new_id = _created_ids[0]
    # Full GET first — verify faststart (moov near front)
    r = client.get(f"{BASE_URL}/api/video/{new_id}/download?auth={ADMIN_TOKEN}")
    assert r.status_code == 200
    assert r.headers.get("accept-ranges") == "bytes"
    body = r.content
    assert body[4:8] == b"ftyp", "not an mp4 (no ftyp)"
    # moov box should be within first ~1MB (faststart)
    head = body[:1_000_000]
    assert b"moov" in head, "moov not near front — faststart missing"

    # Range request
    r2 = client.get(f"{BASE_URL}/api/video/{new_id}/download?auth={ADMIN_TOKEN}",
                    headers={"Range": "bytes=0-1023"})
    assert r2.status_code == 206
    assert r2.headers.get("content-length") == "1024"
    cr = r2.headers.get("content-range", "")
    assert cr.startswith("bytes 0-1023/")


# ---------------- Edit with logo enabled ----------------
def test_edit_with_logo(client):
    body = {"aspect": "1:1", "filter": "warm", "speed": 1.0,
            "logo": {"enabled": True, "x": 0.05, "y": 0.05, "scale": 0.2, "opacity": 0.8}}
    r = client.post(f"{BASE_URL}/api/video/jobs/{SRC_JOB}/edit", json=body, timeout=300)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["options"]["aspect_ratio"] == "1:1"
    _created_ids.append(j["id"])


# ---------------- Delete created edit jobs (cleanup + verify DELETE) ----------------
def test_delete_edited_jobs(client):
    for jid in list(_created_ids):
        r = client.delete(f"{BASE_URL}/api/video/jobs/{jid}")
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # verify gone from list
        lst = client.get(f"{BASE_URL}/api/video/jobs").json()
        assert all(j["id"] != jid for j in lst)


# ---------------- Bad inputs ----------------
def test_edit_missing_job_404(client):
    r = client.post(f"{BASE_URL}/api/video/jobs/does-not-exist/edit",
                    json={"aspect": "9:16", "filter": "none", "speed": 1.0, "logo": {"enabled": False}})
    assert r.status_code == 404

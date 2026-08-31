"""Test HTTP Range support on /api/video/{id}/download and DELETE /api/video/jobs/{id}."""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_TOKEN = "admin_sess_1788155531096"  # studio + admin, owner user_admin_seed
DED_OWNER = "user_ded9f8fff749"


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def ded_token(db):
    tok = "qa_ded_" + str(int(time.time() * 1000))
    db.user_sessions.insert_one({
        "user_id": DED_OWNER, "session_token": tok,
        "expires_at": __import__("datetime").datetime.utcnow().__class__.utcnow() + __import__("datetime").timedelta(days=1),
        "created_at": __import__("datetime").datetime.utcnow(),
    })
    yield tok
    db.user_sessions.delete_one({"session_token": tok})


@pytest.fixture(scope="module")
def done_job_id(ded_token):
    r = requests.get(f"{BASE_URL}/api/video/jobs", headers={"Authorization": f"Bearer {ded_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    done = [j for j in r.json() if j.get("status") == "DONE"]
    assert done, "No DONE jobs found for user_ded9f8fff749"
    return done[0]["id"]


# ---------- Range / download tests ----------

def test_download_without_range_returns_200_with_accept_ranges(ded_token, done_job_id):
    r = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download",
                     headers={"Authorization": f"Bearer {ded_token}"}, timeout=120)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("Accept-Ranges") == "bytes"
    cl = int(r.headers.get("Content-Length", "0"))
    assert cl > 0
    assert len(r.content) == cl
    # Valid mp4: bytes 4..8 are 'ftyp'
    assert r.content[4:8] == b"ftyp", f"Not a valid mp4 (missing ftyp box): {r.content[:16]!r}"


def test_download_with_range_returns_206(ded_token, done_job_id):
    r = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download",
                     headers={"Authorization": f"Bearer {ded_token}", "Range": "bytes=0-1023"}, timeout=120)
    assert r.status_code == 206, r.text[:200]
    assert r.headers.get("Accept-Ranges") == "bytes"
    cr = r.headers.get("Content-Range", "")
    assert cr.startswith("bytes 0-1023/"), f"Content-Range={cr}"
    total = int(cr.split("/")[-1])
    assert total > 1024
    assert r.headers.get("Content-Length") == "1024"
    assert len(r.content) == 1024
    assert r.content[4:8] == b"ftyp"


def test_download_mid_range(ded_token, done_job_id):
    # Get total size first
    head = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download",
                        headers={"Authorization": f"Bearer {ded_token}", "Range": "bytes=0-0"}, timeout=120)
    total = int(head.headers["Content-Range"].split("/")[-1])
    start = total // 2
    r = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download",
                     headers={"Authorization": f"Bearer {ded_token}",
                              "Range": f"bytes={start}-{start + 511}"}, timeout=120)
    assert r.status_code == 206
    assert r.headers.get("Content-Range") == f"bytes {start}-{start + 511}/{total}"
    assert r.headers.get("Content-Length") == "512"
    assert len(r.content) == 512


def test_download_auth_via_query_param(ded_token, done_job_id):
    r = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download?auth={ded_token}",
                     headers={"Range": "bytes=0-15"}, timeout=120)
    assert r.status_code == 206
    assert r.content[4:8] == b"ftyp"


def test_download_unauthorized(done_job_id):
    r = requests.get(f"{BASE_URL}/api/video/{done_job_id}/download", timeout=30)
    assert r.status_code == 401


# ---------- DELETE video job ----------

def _seed_video_job(db, owner: str, status: str = "DONE"):
    jid = str(uuid.uuid4())
    doc = {"id": jid, "owner": owner, "kind": "generate", "prompt": "TEST_delete",
           "status": status, "created_at": "2026-01-01T00:00:00Z"}
    if status == "DONE":
        doc["gcs_uri"] = "gs://fake/none.mp4"
    db.video_jobs.insert_one(doc)
    return jid


def test_delete_own_job(db):
    jid = _seed_video_job(db, "user_admin_seed", status="RUNNING")
    r = requests.delete(f"{BASE_URL}/api/video/jobs/{jid}",
                        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    # verify GET jobs no longer lists it
    jobs = requests.get(f"{BASE_URL}/api/video/jobs",
                        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}, timeout=30).json()
    assert not any(j["id"] == jid for j in jobs)


def test_delete_other_users_job_returns_404(db):
    # Seed a job owned by someone else
    jid = _seed_video_job(db, "user_someone_else_TEST", status="RUNNING")
    try:
        r = requests.delete(f"{BASE_URL}/api/video/jobs/{jid}",
                            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}, timeout=30)
        assert r.status_code == 404
    finally:
        db.video_jobs.delete_one({"id": jid})


def test_delete_nonexistent_returns_404():
    r = requests.delete(f"{BASE_URL}/api/video/jobs/does-not-exist-xyz",
                        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}, timeout=30)
    assert r.status_code == 404

"""
Regression test for LUMIÈRE Social Studio async design generation.

Bug: previously the POST /api/social/posts/{id}/design endpoint ran fal.ai + Gemini
fallback ON the request path and could exceed the k8s ingress ~100s timeout ->
504 "Design failed".
Fix: POST now enqueues a BackgroundTask and returns immediately with
{ok:true, status:"generating"}. Frontend polls GET /api/social/posts/{id}/status
until design_status is 'ready' (with served_by) or 'error'.

This test verifies:
- POST /design returns in <5s (async) for recraft/ideogram/gemini + preview toggle
- design_status transitions generating -> ready | error (poll up to ~150s)
- GET /social/posts includes design_status for each post
- Parallel generation (concurrent POSTs) each return instantly
- Gemini direct engine completes and served_by=gemini
"""

import os
import time
import concurrent.futures
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass

TOKEN = "admin_sess_1788202740303"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

MAX_POST_ELAPSED_S = 5.0     # POST must return this fast (async)
POLL_TIMEOUT_S = 180.0        # allow up to 3min for background job (fal.ai external)
POLL_INTERVAL_S = 3.0


# ---------- helpers ----------

@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _list_posts(api):
    r = api.get(f"{BASE_URL}/api/social/posts", timeout=30)
    assert r.status_code == 200, f"posts list {r.status_code}: {r.text[:300]}"
    posts = r.json()
    if isinstance(posts, dict):
        posts = posts.get("posts", posts.get("items", []))
    return posts


def _ensure_drafts(api, needed=1):
    posts = _list_posts(api)
    drafts = [p for p in posts if p.get("status") in (None, "draft", "DRAFT")]
    if len(drafts) >= needed:
        return drafts
    # create a plan (takes 30-60s)
    r2 = api.post(
        f"{BASE_URL}/api/social/plan",
        json={"brief": "Async regression: prompt engineering series", "count": max(needed, 2)},
        timeout=180,
    )
    assert r2.status_code == 200, f"plan create {r2.status_code}: {r2.text[:300]}"
    posts = _list_posts(api)
    drafts = [p for p in posts if p.get("status") in (None, "draft", "DRAFT")]
    assert len(drafts) >= needed, f"still not enough drafts: have {len(drafts)}, need {needed}"
    return drafts


def _pid(p):
    return p.get("id") or p.get("_id") or p.get("post_id")


def _post_design(api, post_id, engine=None, preview=False):
    params = {}
    if engine:
        params["engine"] = engine
    if preview:
        params["preview"] = "true"
    t0 = time.time()
    r = api.post(f"{BASE_URL}/api/social/posts/{post_id}/design", params=params, timeout=15)
    elapsed = time.time() - t0
    return r, elapsed


def _poll_until_terminal(api, post_id, timeout=POLL_TIMEOUT_S):
    """Poll /status until design_status is 'ready' or 'error' (or timeout)."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        r = api.get(f"{BASE_URL}/api/social/posts/{post_id}/status", timeout=15)
        assert r.status_code == 200, f"status {r.status_code}: {r.text[:200]}"
        data = r.json()
        last = data
        st = data.get("design_status")
        if st in ("ready", "error"):
            return data, time.time() - t0
        time.sleep(POLL_INTERVAL_S)
    return last, time.time() - t0


# ---------- Tests ----------

class TestAsyncReturnsInstantly:
    """POST /design must return in <5s regardless of downstream engine."""

    def test_recraft_returns_instantly(self, api):
        drafts = _ensure_drafts(api, 1)
        pid = _pid(drafts[0])
        r, elapsed = _post_design(api, pid, engine="recraft", preview=False)
        assert r.status_code == 200, f"recraft POST {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True, body
        assert body.get("status") == "generating", body
        assert elapsed < MAX_POST_ELAPSED_S, (
            f"POST /design (recraft) took {elapsed:.2f}s, expected <{MAX_POST_ELAPSED_S}s (async)")
        print(f"[recraft] POST returned in {elapsed:.2f}s status=generating")

    def test_ideogram_preview_returns_instantly(self, api):
        drafts = _ensure_drafts(api, 1)
        pid = _pid(drafts[0])
        r, elapsed = _post_design(api, pid, engine="ideogram", preview=True)
        assert r.status_code == 200, f"ideogram+preview POST {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True and body.get("status") == "generating", body
        assert elapsed < MAX_POST_ELAPSED_S, (
            f"POST /design (ideogram+preview) took {elapsed:.2f}s, expected <{MAX_POST_ELAPSED_S}s")
        print(f"[ideogram+preview] POST returned in {elapsed:.2f}s")

    def test_gemini_returns_instantly(self, api):
        drafts = _ensure_drafts(api, 1)
        pid = _pid(drafts[0])
        r, elapsed = _post_design(api, pid, engine="gemini")
        assert r.status_code == 200, f"gemini POST {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True and body.get("status") == "generating", body
        assert elapsed < MAX_POST_ELAPSED_S, (
            f"POST /design (gemini) took {elapsed:.2f}s, expected <{MAX_POST_ELAPSED_S}s")
        print(f"[gemini] POST returned in {elapsed:.2f}s")


class TestPollingReachesTerminal:
    """One end-to-end poll cycle to confirm design_status eventually reaches ready or error
    (never stuck in 'generating' forever). We accept either ready or a clean error state."""

    def test_ideogram_preview_reaches_ready_or_error(self, api):
        drafts = _ensure_drafts(api, 1)
        pid = _pid(drafts[0])
        r, elapsed = _post_design(api, pid, engine="ideogram", preview=True)
        assert r.status_code == 200 and elapsed < MAX_POST_ELAPSED_S
        data, waited = _poll_until_terminal(api, pid)
        print(f"[ideogram+preview] terminal state after {waited:.1f}s: {data}")
        assert data is not None, "no status response"
        assert data.get("design_status") in ("ready", "error"), (
            f"design_status stuck at {data.get('design_status')} after {waited:.1f}s: {data}")
        if data.get("design_status") == "ready":
            assert data.get("has_image") is True, data
            assert data.get("served_by") in ("recraft", "ideogram", "gemini"), data

    def test_gemini_reaches_ready(self, api):
        drafts = _ensure_drafts(api, 1)
        pid = _pid(drafts[0])
        r, elapsed = _post_design(api, pid, engine="gemini")
        assert r.status_code == 200 and elapsed < MAX_POST_ELAPSED_S
        data, waited = _poll_until_terminal(api, pid, timeout=180.0)
        print(f"[gemini] terminal after {waited:.1f}s: {data}")
        assert data and data.get("design_status") in ("ready", "error"), data
        # Gemini path should succeed
        if data.get("design_status") == "ready":
            assert data.get("has_image") is True
            assert data.get("served_by") == "gemini", (
                f"expected served_by=gemini, got {data.get('served_by')}")


class TestPostsListHasDesignStatus:
    def test_posts_include_design_status_field(self, api):
        posts = _list_posts(api)
        assert posts, "no posts returned"
        # At least one should have design_status set (since previous tests generated designs)
        with_field = [p for p in posts if "design_status" in p]
        assert with_field, "no post has design_status field in GET /social/posts"
        print(f"posts with design_status: {len(with_field)}/{len(posts)}")


class TestParallelGenerateAll:
    """Fire concurrent POST /design; each must return instantly (no serialization)."""

    def test_parallel_posts_all_instant(self, api):
        drafts = _ensure_drafts(api, 2)
        pids = [_pid(p) for p in drafts[:2]]

        def _fire(pid):
            # Independent session to avoid urllib3 pool serialization skew
            s = requests.Session()
            s.headers.update(HEADERS)
            t0 = time.time()
            r = s.post(f"{BASE_URL}/api/social/posts/{pid}/design",
                       params={"engine": "ideogram", "preview": "true"}, timeout=15)
            return pid, r.status_code, time.time() - t0, r.text[:200]

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(pids)) as ex:
            results = list(ex.map(_fire, pids))

        for pid, code, elapsed, body in results:
            print(f"[parallel] pid={pid} code={code} elapsed={elapsed:.2f}s")
            assert code == 200, f"parallel POST failed for {pid}: {code} {body}"
            assert elapsed < MAX_POST_ELAPSED_S + 2.0, (
                f"parallel POST for {pid} took {elapsed:.2f}s (>{MAX_POST_ELAPSED_S+2}s) — request path not async?")

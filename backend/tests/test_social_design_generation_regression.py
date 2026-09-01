"""
Regression test for Lumiere Social Studio 'Design failed' bug fix.

Bug: fal.ai Recraft generation for 'Minimal Corporativo' style could exceed the
~100s k8s ingress timeout, returning 504 -> UI shows 'Design failed'.
Fix: fal_images.generate now caps the fal call at 55s so the endpoint falls
back to Gemini before ingress timeout. Endpoint should ALWAYS return 200 with a
stored image.

Only failure conditions:
- non-200 response
- returned payload missing image_url / ok=false
- GET /api/social/posts/{id}/image not 200 image/*
- response time exceeding ~90s
"""

import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Read frontend/.env fallback
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


# ---------- Shared helpers ----------

@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _get_draft_post_id(api):
    r = api.get(f"{BASE_URL}/api/social/posts", timeout=30)
    assert r.status_code == 200, f"posts list failed: {r.status_code} {r.text[:300]}"
    posts = r.json()
    if isinstance(posts, dict):
        posts = posts.get("posts", posts.get("items", []))
    drafts = [p for p in posts if (p.get("status") in (None, "draft", "DRAFT"))]
    if not drafts:
        # create plan
        r2 = api.post(
            f"{BASE_URL}/api/social/plan",
            json={"brief": "Prompt engineering educational series", "count": 2},
            timeout=120,
        )
        assert r2.status_code == 200, f"plan create failed: {r2.status_code} {r2.text[:300]}"
        r = api.get(f"{BASE_URL}/api/social/posts", timeout=30)
        posts = r.json()
        if isinstance(posts, dict):
            posts = posts.get("posts", posts.get("items", []))
        drafts = [p for p in posts if (p.get("status") in (None, "draft", "DRAFT"))]
    assert drafts, "No draft posts available even after plan creation"
    return drafts[0].get("id") or drafts[0].get("_id") or drafts[0].get("post_id")


def _put_brand(api, image_style):
    payload = {
        "image_style": image_style,
        "colors": ["#111111", "#0c4c4b", "#D6A85F"],
        "image_engine": "recraft",
    }
    r = api.put(f"{BASE_URL}/api/social/brand", json=payload, timeout=30)
    assert r.status_code == 200, f"brand PUT failed: {r.status_code} {r.text[:300]}"


def _design_and_verify(api, post_id, engine, max_seconds=95.0):
    t0 = time.time()
    r = api.post(
        f"{BASE_URL}/api/social/posts/{post_id}/design",
        params={"engine": engine},
        timeout=max_seconds + 10,
    )
    elapsed = time.time() - t0
    assert r.status_code == 200, (
        f"[engine={engine}] design endpoint returned {r.status_code} in {elapsed:.1f}s: {r.text[:400]}"
    )
    data = r.json()
    assert data.get("ok") is True, f"[engine={engine}] ok!=true: {data}"
    assert data.get("image_url"), f"[engine={engine}] missing image_url: {data}"
    assert elapsed < max_seconds, f"[engine={engine}] too slow: {elapsed:.1f}s (>{max_seconds}s)"

    # Fetch served image
    ri = api.get(f"{BASE_URL}/api/social/posts/{post_id}/image", timeout=30)
    assert ri.status_code == 200, f"[engine={engine}] image fetch {ri.status_code}: {ri.text[:200]}"
    ctype = ri.headers.get("content-type", "")
    assert ctype.startswith("image/"), f"[engine={engine}] bad content-type: {ctype}"
    assert len(ri.content) > 500, f"[engine={engine}] image too small ({len(ri.content)}b)"
    return elapsed


# ---------- Tests: Minimal Corporativo (the failing scenario) ----------

class TestMinimalStyleDesign:
    """The exact bug scenario: brand style Minimal + each supported engine must succeed."""

    def test_set_brand_minimal(self, api):
        _put_brand(api, "minimal")

    def test_minimal_recraft(self, api):
        post_id = _get_draft_post_id(api)
        elapsed = _design_and_verify(api, post_id, "recraft")
        print(f"[minimal/recraft] OK in {elapsed:.1f}s")

    def test_minimal_ideogram(self, api):
        post_id = _get_draft_post_id(api)
        elapsed = _design_and_verify(api, post_id, "ideogram")
        print(f"[minimal/ideogram] OK in {elapsed:.1f}s")

    def test_minimal_gemini(self, api):
        post_id = _get_draft_post_id(api)
        elapsed = _design_and_verify(api, post_id, "gemini")
        print(f"[minimal/gemini] OK in {elapsed:.1f}s")


# ---------- Tests: 3D illustration still works ----------

class TestIllustration3DStillWorks:
    def test_illustration3d_recraft(self, api):
        _put_brand(api, "illustration3d")
        post_id = _get_draft_post_id(api)
        elapsed = _design_and_verify(api, post_id, "recraft")
        print(f"[illustration3d/recraft] OK in {elapsed:.1f}s")

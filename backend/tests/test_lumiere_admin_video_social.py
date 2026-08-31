"""LUMIÈRE backend regression:
- /auth/me admin flag + /account entitlements
- /admin/* admin routes + non-admin 403
- /video/generate GATING (free 403, studio passes to gateway)
- /social/* full CRUD flow + gating

Run: pytest -v --tb=short --junitxml=/app/test_reports/pytest/iteration_7.xml
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lumiere-studio-7.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "admin_sess_1788155531096"
FREE_TOKEN = "free_sess_test_1788155777682"


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- auth / account ----------
class TestAuthAccount:
    def test_admin_me(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_admin"] is True
        assert d["plan"] == "studio"
        assert d["email"] == "admin@getlumiere.ai"

    def test_admin_account_entitlements(self):
        r = requests.get(f"{BASE_URL}/api/account", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_admin"] is True
        assert d["plan"]["id"] == "studio"
        ent = d.get("entitlements") or {}
        assert ent.get("video") is True
        assert ent.get("social") is True
        assert "ai_generations" in (d.get("limits") or {})
        assert "ai_generations" in (d.get("usage") or {})

    def test_free_account_entitlements(self):
        r = requests.get(f"{BASE_URL}/api/account", headers=_h(FREE_TOKEN), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        ent = d.get("entitlements") or {}
        assert ent.get("video") in (False, None)
        assert ent.get("social") in (False, None)


# ---------- admin routes ----------
class TestAdminRoutes:
    def test_overview(self):
        r = requests.get(f"{BASE_URL}/api/admin/overview", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("users", "experiences", "video_jobs", "social_posts"):
            assert k in d and isinstance(d[k], int)

    def test_plans_get_and_update(self):
        r = requests.get(f"{BASE_URL}/api/admin/plans", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        plans = r.json()["plans"]
        ids = [p["id"] for p in plans]
        assert set(["free", "creator", "studio"]).issubset(set(ids))

        # Edit creator monthly price to 55
        edited = []
        original_creator_price = None
        for p in plans:
            if p["id"] == "creator":
                original_creator_price = ((p.get("price") or {}).get("monthly"))
                p.setdefault("price", {})["monthly"] = 55
            edited.append(p)
        r2 = requests.put(f"{BASE_URL}/api/admin/plans", headers=_h(ADMIN_TOKEN),
                          json={"plans": edited}, timeout=30)
        assert r2.status_code == 200, r2.text
        # Re-read and verify
        r3 = requests.get(f"{BASE_URL}/api/admin/plans", headers=_h(ADMIN_TOKEN), timeout=30)
        creator = next(p for p in r3.json()["plans"] if p["id"] == "creator")
        assert (creator.get("price") or {}).get("monthly") == 55

        # Restore
        if original_creator_price is not None:
            plans2 = r3.json()["plans"]
            for p in plans2:
                if p["id"] == "creator":
                    p["price"]["monthly"] = original_creator_price
            requests.put(f"{BASE_URL}/api/admin/plans", headers=_h(ADMIN_TOKEN),
                         json={"plans": plans2}, timeout=30)

    def test_users_list(self):
        r = requests.get(f"{BASE_URL}/api/admin/users", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) > 0
        # each user has plan + is_admin
        u0 = users[0]
        assert "plan" in u0 and "is_admin" in u0

    def test_set_user_plan(self):
        # Find the free test user, flip to creator then back to free
        r = requests.get(f"{BASE_URL}/api/admin/users", headers=_h(ADMIN_TOKEN), timeout=30)
        free_users = [u for u in r.json() if u["email"].startswith("free.test.")]
        assert free_users, "no free test user seeded"
        uid = free_users[0]["user_id"]
        r2 = requests.post(f"{BASE_URL}/api/admin/users/{uid}/plan",
                           headers=_h(ADMIN_TOKEN), json={"plan": "creator"}, timeout=30)
        assert r2.status_code == 200, r2.text
        assert r2.json()["plan"] == "creator"
        # revert
        r3 = requests.post(f"{BASE_URL}/api/admin/users/{uid}/plan",
                           headers=_h(ADMIN_TOKEN), json={"plan": "free"}, timeout=30)
        assert r3.status_code == 200

    def test_video_jobs_list(self):
        r = requests.get(f"{BASE_URL}/api/admin/video-jobs", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_social_posts_list(self):
        r = requests.get(f"{BASE_URL}/api/admin/social-posts", headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_non_admin_403(self):
        for path in ("/api/admin/overview", "/api/admin/plans", "/api/admin/users",
                     "/api/admin/video-jobs", "/api/admin/social-posts"):
            r = requests.get(f"{BASE_URL}{path}", headers=_h(FREE_TOKEN), timeout=30)
            assert r.status_code == 403, f"{path} expected 403 got {r.status_code}"


# ---------- video gating ----------
class TestVideoGating:
    def test_free_blocked(self):
        r = requests.post(f"{BASE_URL}/api/video/generate", headers=_h(FREE_TOKEN),
                          json={"prompt": "cinematic sunrise over sea"}, timeout=30)
        assert r.status_code == 403, r.text
        assert r.json().get("detail") == "video_not_entitled"

    def test_studio_passes_entitlement(self):
        """Studio user should NOT be blocked at gating; will fail at gateway step (502/503 expected)."""
        r = requests.post(f"{BASE_URL}/api/video/generate", headers=_h(ADMIN_TOKEN),
                          json={"prompt": "TEST_gating cinematic sunrise", "aspect": "16:9",
                                "duration": 4}, timeout=60)
        # 200 (if gateway happens to work), 502/503 (gateway not deployed) OR
        # 403 quota_exceeded (if monthly quota already hit). NEVER video_not_entitled.
        # We must NEVER see video_not_entitled for studio user
        if r.status_code == 403:
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = r.text
            assert detail != "video_not_entitled", f"studio should be entitled: {r.text}"
            assert detail == "quota_exceeded", r.text
        else:
            # 200 gateway ok, or 502/503/504 (gateway not deployed / timeout) — all acceptable
            assert r.status_code in (200, 500, 502, 503, 504), r.text


# ---------- social studio ----------
_created_post_id = None


class TestSocialStudio:
    def test_free_blocked_on_plan(self):
        r = requests.post(f"{BASE_URL}/api/social/plan", headers=_h(FREE_TOKEN),
                          json={"brief": "TEST_ some brief", "count": 2}, timeout=30)
        assert r.status_code == 403
        assert r.json().get("detail") == "social_not_entitled"

    def test_plan_generate(self):
        global _created_post_id
        r = requests.post(f"{BASE_URL}/api/social/plan", headers=_h(ADMIN_TOKEN),
                          json={"brief": "TEST_ launch a boutique coffee brand", "count": 2},
                          timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "plan" in d
        posts = d.get("posts") or []
        assert len(posts) >= 1
        p = posts[0]
        assert p.get("id")
        assert p.get("caption") and isinstance(p["caption"], dict)
        assert "en" in p["caption"] and "es" in p["caption"]
        assert p.get("network") in ["instagram", "facebook", "x", "linkedin", "tiktok"]
        assert p.get("design_prompt")
        _created_post_id = p["id"]

    def test_design_image(self):
        assert _created_post_id, "no post from previous test"
        r = requests.post(f"{BASE_URL}/api/social/posts/{_created_post_id}/design",
                          headers=_h(ADMIN_TOKEN), timeout=120)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_get_image(self):
        assert _created_post_id
        r = requests.get(f"{BASE_URL}/api/social/posts/{_created_post_id}/image",
                         headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 500

    def test_update_post(self):
        assert _created_post_id
        r = requests.put(f"{BASE_URL}/api/social/posts/{_created_post_id}",
                         headers=_h(ADMIN_TOKEN),
                         json={"network": "linkedin",
                               "caption": {"en": "TEST_ updated", "es": "TEST_ actualizado"}},
                         timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("network") == "linkedin"

    def test_schedule(self):
        assert _created_post_id
        r = requests.post(f"{BASE_URL}/api/social/posts/{_created_post_id}/schedule",
                          headers=_h(ADMIN_TOKEN),
                          json={"network": "instagram",
                                "scheduled_at": "2026-12-31T10:00:00Z"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "scheduled"

    def test_publish(self):
        assert _created_post_id
        r = requests.post(f"{BASE_URL}/api/social/posts/{_created_post_id}/publish",
                          headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        assert r.json().get("status") == "published"

    def test_delete(self):
        assert _created_post_id
        r = requests.delete(f"{BASE_URL}/api/social/posts/{_created_post_id}",
                            headers=_h(ADMIN_TOKEN), timeout=30)
        assert r.status_code == 200
        # verify gone
        r2 = requests.get(f"{BASE_URL}/api/social/posts/{_created_post_id}/image",
                          headers=_h(ADMIN_TOKEN), timeout=15)
        assert r2.status_code == 404

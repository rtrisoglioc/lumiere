"""Iteration 13 backend tests: PayPal config/create-order + Social image overlay + captions field acceptance."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lumiere-studio-7.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "admin_sess_1788202740303"
HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


# -------- PayPal --------
class TestPayPal:
    def test_config(self):
        r = requests.get(f"{BASE_URL}/api/payments/config", timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["enabled"] is True
        assert j["mode"] == "sandbox"
        assert j["currency"] == "USD"
        assert isinstance(j["client_id"], str) and len(j["client_id"]) > 10

    def test_create_order_creator_monthly(self):
        r = requests.post(f"{BASE_URL}/api/payments/paypal/create-order",
                          headers=HEADERS, json={"plan": "creator", "cycle": "monthly"}, timeout=45)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["amount"] == 49
        assert j["currency"] == "USD"
        assert isinstance(j["id"], str) and len(j["id"]) > 5

    def test_create_order_studio_yearly(self):
        r = requests.post(f"{BASE_URL}/api/payments/paypal/create-order",
                          headers=HEADERS, json={"plan": "studio", "cycle": "yearly"}, timeout=45)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["amount"] == 1428
        assert isinstance(j["id"], str) and len(j["id"]) > 5

    def test_create_order_free_rejected(self):
        r = requests.post(f"{BASE_URL}/api/payments/paypal/create-order",
                          headers=HEADERS, json={"plan": "free"}, timeout=30)
        assert r.status_code == 400
        assert "plan_not_payable" in r.text


# -------- Social overlay flow --------
class TestSocialOverlay:
    post_id = None
    base_bytes = None

    def test_01_create_plan(self):
        r = requests.post(f"{BASE_URL}/api/social/plan",
                          headers=HEADERS,
                          json={"brief": "Cinematic road trip series, warm playful tone", "count": 2},
                          timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        posts = j.get("posts") or j.get("plan", {}).get("posts") or []
        assert len(posts) >= 1, j
        TestSocialOverlay.post_id = posts[0]["id"]

    def test_02_generate_design(self):
        assert TestSocialOverlay.post_id
        r = requests.post(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/design",
                          headers=HEADERS, json={}, timeout=180)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # fetch base image
        r2 = requests.get(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/image",
                          headers=HEADERS, timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/png")
        assert len(r2.content) > 500
        TestSocialOverlay.base_bytes = r2.content

    def test_03_apply_text_overlay(self):
        assert TestSocialOverlay.post_id and TestSocialOverlay.base_bytes
        payload = {"text": {"enabled": True, "content": "ROAD TRIP", "position": "bottom",
                            "color": "#FFFFFF", "size": 0.09}}
        r = requests.post(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/overlay",
                          headers=HEADERS, json=payload, timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert "image_url" in j

        r2 = requests.get(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/image",
                          headers=HEADERS, timeout=60)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/png")
        assert r2.content != TestSocialOverlay.base_bytes, "overlay image must differ from base"

    def test_04_clear_overlay_reverts(self):
        assert TestSocialOverlay.post_id
        payload = {"text": {"enabled": False}, "logo": {"enabled": False}}
        r = requests.post(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/overlay",
                          headers=HEADERS, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("cleared") is True

        r2 = requests.get(f"{BASE_URL}/api/social/posts/{TestSocialOverlay.post_id}/image",
                          headers=HEADERS, timeout=60)
        assert r2.status_code == 200
        assert r2.content == TestSocialOverlay.base_bytes, "should revert to base"


# -------- Captions field schema acceptance --------
class TestCaptionsFieldAcceptance:
    def test_pro_edit_captions_field_no_422(self):
        # Find a ready cut for the admin user (any experience)
        r = requests.get(f"{BASE_URL}/api/experiences", headers=HEADERS, timeout=30)
        if r.status_code != 200:
            pytest.skip("cannot list experiences")
        exps = r.json() or []
        ready_cut_id = None
        for e in exps[:20]:
            eid = e.get("id")
            if not eid:
                continue
            cr = requests.get(f"{BASE_URL}/api/experiences/{eid}/cuts", headers=HEADERS, timeout=30)
            if cr.status_code != 200:
                continue
            for c in cr.json() or []:
                if c.get("status") in ("ready", "done", "DONE", "READY") and c.get("video_path"):
                    ready_cut_id = c["id"]
                    break
            if ready_cut_id:
                break
        if not ready_cut_id:
            pytest.skip("no ready cut found for captions schema test")
        r = requests.post(f"{BASE_URL}/api/cuts/{ready_cut_id}/pro-edit",
                          headers=HEADERS,
                          json={"captions": {"enabled": True, "style": "pop", "lang": "es"}},
                          timeout=180)
        # We only assert schema acceptance (no 422)
        assert r.status_code != 422, f"pro-edit rejected captions schema: {r.text}"

    def test_video_edit_captions_field_no_422(self):
        r = requests.get(f"{BASE_URL}/api/video/jobs", headers=HEADERS, timeout=30)
        if r.status_code != 200:
            pytest.skip("cannot list video jobs")
        jobs = r.json() or []
        done = [j for j in jobs if (j.get("status") in ("DONE", "done", "ready"))]
        if not done:
            pytest.skip("no DONE video job for captions schema test")
        jid = done[0]["id"]
        r = requests.post(f"{BASE_URL}/api/video/jobs/{jid}/edit",
                          headers=HEADERS,
                          json={"captions": {"enabled": True, "style": "pop", "lang": "es"}},
                          timeout=180)
        assert r.status_code != 422, f"video edit rejected captions schema: {r.text}"

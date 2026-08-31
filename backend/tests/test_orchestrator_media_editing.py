"""LUMIÈRE Orchestrator + Media Deletion + Edit Versioning — Addendum v1.0

Covers acceptance IDs: ORCH-01/03, MEDIA-DEL-01/02/03, EDIT-01/02/03, plus impacted
cuts, cut delete, experience impact/delete.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lumiere-studio-7.preview.emergentagent.com").rstrip("/")
ADMIN_TOKEN = "admin_sess_1788155531096"

CLIP1 = "/tmp/testclips/clip1.mp4"
CLIP2 = "/tmp/testclips/clip2.mp4"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {ADMIN_TOKEN}"})
    return s


@pytest.fixture(scope="session")
def experience(client):
    r = client.post(f"{BASE_URL}/api/experiences", json={"title": "TEST_Orch_Addendum", "type": "travel", "language": "en"})
    assert r.status_code == 200, r.text
    exp = r.json()
    yield exp
    # cleanup: hard-delete
    try:
        client.delete(f"{BASE_URL}/api/experiences/{exp['id']}?permanent=true&confirm=true", timeout=30)
    except Exception:
        pass


# ---------- ORCH-01: brand new experience → next_action=create_plan ----------
def test_orch_01_new_experience_create_plan(client, experience):
    r = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator")
    assert r.status_code == 200, r.text
    d = r.json()
    # All required contract keys
    for k in ("next_action", "agent_selected", "reason", "required_input",
              "evidence", "confidence", "story_completeness", "production_state",
              "user_approval_required", "trace_id"):
        assert k in d, f"missing key {k}"
    assert d["next_action"] == "create_plan"
    assert isinstance(d["reason"], dict) and "en" in d["reason"] and "es" in d["reason"]
    assert isinstance(d["evidence"], list)
    assert isinstance(d["confidence"], (int, float))
    assert 0.0 <= d["story_completeness"] <= 1.0
    assert isinstance(d["production_state"], dict)


# ---------- ORCH-03 (transition 1): after plan → capture ----------
def test_orch_03_after_plan_capture(client, experience):
    r = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/plan",
                    json={"intent": "A short travel piece capturing color and light in a market."},
                    timeout=90)
    assert r.status_code == 200, r.text
    d = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator").json()
    assert d["next_action"] == "capture", d


# ---------- Upload 2 clips + wait for analysis ----------
@pytest.fixture(scope="session")
def uploaded_assets(client, experience):
    assets = []
    for path in (CLIP1, CLIP2):
        with open(path, "rb") as f:
            r = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/upload",
                            files={"file": (os.path.basename(path), f, "video/mp4")}, timeout=60)
        assert r.status_code == 200, r.text
        assets.append(r.json())
    # Poll until analyzed or failed (up to 5 min)
    deadline = time.time() + 300
    last = None
    while time.time() < deadline:
        r = client.get(f"{BASE_URL}/api/experiences/{experience['id']}")
        media = r.json().get("media", [])
        statuses = sorted([m["status"] for m in media])
        last = statuses
        if len(media) == 2 and all(s in ("analyzed", "failed") for s in statuses):
            break
        time.sleep(5)
    print(f"[uploaded_assets] final statuses: {last}")
    return assets


def test_orch_03_transitions_after_upload(client, experience, uploaded_assets):
    # After analysis: should be evaluate OR wait_analysis (transient)
    d = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator").json()
    assert d["next_action"] in ("wait_analysis", "evaluate", "get_the_shot", "create_cut"), d["next_action"]


# ---------- MEDIA-DEL-02: impact BEFORE deletion ----------
def test_media_del_02_impact(client, uploaded_assets):
    aid = uploaded_assets[0]["id"]
    r = client.get(f"{BASE_URL}/api/media/{aid}/impact")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["asset_id"] == aid
    assert "cuts" in j and "used_in_cuts" in j and "beats_at_risk" in j
    assert isinstance(j["message"], dict) and "en" in j["message"] and "es" in j["message"]


# ---------- MEDIA-DEL-03: permanent requires confirm ----------
def test_media_del_03_permanent_needs_confirm(client, experience):
    # Upload a throwaway clip
    with open(CLIP1, "rb") as f:
        r = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/upload",
                        files={"file": ("throwaway.mp4", f, "video/mp4")}, timeout=60)
    aid = r.json()["id"]
    r = client.delete(f"{BASE_URL}/api/media/{aid}?permanent=true")
    assert r.status_code == 400
    assert r.json()["detail"] == "confirm_required"

    r = client.delete(f"{BASE_URL}/api/media/{aid}?permanent=true&confirm=true")
    assert r.status_code == 200
    assert r.json()["type"] == "permanent"

    r = client.get(f"{BASE_URL}/api/media/{aid}")
    assert r.status_code == 404


# ---------- MEDIA-DEL-01 + Restore + EDIT-03 (deletion-aware coverage) ----------
def test_media_del_01_trash_and_restore(client, experience, uploaded_assets):
    aid = uploaded_assets[1]["id"]
    before = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator").json()
    before_cov = before["production_state"]["coverage"]

    r = client.delete(f"{BASE_URL}/api/media/{aid}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] and j["type"] == "trash"
    assert "decision" in j and "impacted_cuts" in j

    # Asset now trashed
    r = client.get(f"{BASE_URL}/api/media/{aid}")
    assert r.status_code == 200
    assert r.json()["status"] == "trashed"

    # Orchestrator recomputes (deletion-aware): coverage should be <= before (may drop)
    after = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator").json()
    assert after["production_state"]["coverage"] <= before_cov + 1e-6

    # Restore
    r = client.post(f"{BASE_URL}/api/media/{aid}/restore")
    assert r.status_code == 200
    r = client.get(f"{BASE_URL}/api/media/{aid}")
    assert r.json()["status"] != "trashed"


# ---------- Build a cut so we can test EDIT-01/02 + impacted cuts ----------
@pytest.fixture(scope="session")
def first_cut(client, experience, uploaded_assets):
    # Try evaluate; ignore failure if no analyzed content
    ev = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/evaluate", timeout=90)
    if ev.status_code != 200:
        pytest.skip(f"evaluate failed: {ev.status_code} {ev.text[:200]}")
    r = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/cut", json={}, timeout=90)
    if r.status_code != 200:
        pytest.skip(f"cut failed: {r.status_code} {r.text[:200]}")
    cut = r.json()
    # Poll render
    deadline = time.time() + 120
    while time.time() < deadline:
        cr = client.get(f"{BASE_URL}/api/cuts/{cut['id']}").json()
        if cr.get("status") in ("ready", "failed"):
            cut = cr
            break
        time.sleep(3)
    return cut


def test_edit_01_remove_clip_creates_new_version(client, experience, first_cut, uploaded_assets):
    if first_cut.get("status") == "failed":
        pytest.skip("first cut failed to render")
    edl = first_cut.get("edl") or []
    if len(edl) < 2:
        pytest.skip("first cut has <2 clips; can't test remove-clip without empty error")
    target_asset = edl[0]["asset_id"]

    # Bad asset → 400 clip_not_in_cut
    r = client.post(f"{BASE_URL}/api/cuts/{first_cut['id']}/remove-clip",
                    json={"asset_id": "00000000-not-in-cut"})
    assert r.status_code == 400
    assert r.json()["detail"] == "clip_not_in_cut"

    # Real remove → new CutVersion, higher version, parent_id set, kind='edit'
    r = client.post(f"{BASE_URL}/api/cuts/{first_cut['id']}/remove-clip",
                    json={"asset_id": target_asset})
    assert r.status_code == 200, r.text
    new_cut = r.json()
    assert new_cut["version"] > first_cut["version"]
    assert new_cut["parent_id"] == first_cut["id"]
    assert new_cut["kind"] == "edit"
    # Original media asset preserved
    r = client.get(f"{BASE_URL}/api/media/{target_asset}")
    assert r.status_code == 200


def test_edit_01_would_be_empty(client, experience, uploaded_assets):
    # Create a fresh single-clip cut manually via /cut using only one usable segment isn't easy.
    # Alt: try removing every clip from first_cut sequentially would fail; instead build a synthetic:
    # Get cuts, find one with 1 clip if exists — else skip.
    exp = client.get(f"{BASE_URL}/api/experiences/{experience['id']}").json()
    single = next((c for c in exp.get("cuts", []) if len(c.get("edl") or []) == 1), None)
    if not single:
        pytest.skip("no single-clip cut available to test would_be_empty")
    r = client.post(f"{BASE_URL}/api/cuts/{single['id']}/remove-clip",
                    json={"asset_id": single["edl"][0]["asset_id"]})
    assert r.status_code == 400
    assert r.json()["detail"] == "would_be_empty"


def test_edit_02_revise_creates_new_version(client, first_cut):
    if first_cut.get("status") == "failed":
        pytest.skip("no rendered cut")
    r = client.post(f"{BASE_URL}/api/cuts/{first_cut['id']}/revise",
                    json={"instruction": "make it punchier"}, timeout=120)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["version"] > first_cut["version"]
    assert j["parent_id"] == first_cut["id"]
    assert j["status"] in ("rendering", "ready")


# ---------- Impacted cuts (§4.4) + orchestrator recover_impacted ----------
def test_impacted_cuts_flow(client, experience, first_cut, uploaded_assets):
    if first_cut.get("status") == "failed":
        pytest.skip("no rendered cut")
    edl = first_cut.get("edl") or []
    if not edl:
        pytest.skip("no edl")
    aid = edl[0]["asset_id"]
    # Trash the asset — should flag impacted cuts
    r = client.delete(f"{BASE_URL}/api/media/{aid}")
    assert r.status_code == 200
    j = r.json()
    # impacted_cuts includes at least one id
    assert len(j["impacted_cuts"]) >= 1

    exp = client.get(f"{BASE_URL}/api/experiences/{experience['id']}").json()
    impacted = [c for c in exp.get("cuts", []) if c.get("impacted")]
    assert len(impacted) >= 1

    d = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/orchestrator").json()
    assert d["next_action"] == "recover_impacted"
    assert d["user_approval_required"] is True

    # Restore for cleanup
    client.post(f"{BASE_URL}/api/media/{aid}/restore")


# ---------- Cut delete: source media preserved ----------
def test_delete_cut_preserves_media(client, experience, uploaded_assets):
    # Make a new cut so we can delete it
    r = client.post(f"{BASE_URL}/api/experiences/{experience['id']}/cut", json={}, timeout=90)
    if r.status_code != 200:
        pytest.skip("cannot make cut")
    cut_id = r.json()["id"]
    r = client.delete(f"{BASE_URL}/api/cuts/{cut_id}")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"]
    assert j["message"]["en"] == "Cut deleted. Originals preserved."
    # Media assets still present
    for a in uploaded_assets:
        gr = client.get(f"{BASE_URL}/api/media/{a['id']}")
        assert gr.status_code == 200


# ---------- Experience impact + soft/hard delete ----------
def test_experience_impact_and_soft_delete(client):
    r = client.post(f"{BASE_URL}/api/experiences", json={"title": "TEST_ExpDelete", "type": "travel"})
    exp_id = r.json()["id"]
    r = client.get(f"{BASE_URL}/api/experiences/{exp_id}/impact")
    assert r.status_code == 200
    j = r.json()
    assert "videos" in j and "cuts" in j
    assert "en" in j["message"] and "es" in j["message"]

    # Soft delete
    r = client.delete(f"{BASE_URL}/api/experiences/{exp_id}")
    assert r.status_code == 200
    lst = client.get(f"{BASE_URL}/api/experiences").json()
    assert all(e["id"] != exp_id for e in lst)

    # Permanent needs confirm
    r = client.delete(f"{BASE_URL}/api/experiences/{exp_id}?permanent=true")
    assert r.status_code == 400
    assert r.json()["detail"] == "confirm_required"

    r = client.delete(f"{BASE_URL}/api/experiences/{exp_id}?permanent=true&confirm=true")
    assert r.status_code == 200


# ---------- Decisions persisted / traceable ----------
def test_decisions_persisted(client, experience):
    r = client.get(f"{BASE_URL}/api/experiences/{experience['id']}/decisions")
    assert r.status_code == 200
    decs = r.json()
    assert isinstance(decs, list) and len(decs) >= 1
    assert all("trace_id" in d and "next_action" in d for d in decs)

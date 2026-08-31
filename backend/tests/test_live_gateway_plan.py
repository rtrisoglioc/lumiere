"""Iteration 6: LIVE Vertex AI Agent Engine gateway validation.

Validates the plan flow (context->director->cinematographer) through the real
Cloud Run gateway (POST /agent) as well as trace provenance and regression health.
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lumiere-studio-7.preview.emergentagent.com").rstrip("/")
BEARER = "e2e_1788105676"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json"})
    return sess


# ---------- Regression health ----------
class TestRegressionHealth:
    def test_agent_health(self, s):
        r = s.get(f"{BASE_URL}/api/agent/health", timeout=20)
        assert r.status_code == 200, r.text
        print("agent/health:", r.text[:400])

    def test_partner_health(self, s):
        r = s.get(f"{BASE_URL}/api/partner/health", timeout=20)
        assert r.status_code == 200, r.text

    def test_auth_me(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=20)
        assert r.status_code == 200, r.text


# ---------- LIVE gateway plan flow ----------
class TestLiveGatewayPlan:
    @pytest.fixture(scope="class")
    def exp_id(self):
        sess = requests.Session()
        sess.headers.update({"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json"})
        payload = {
            "title": "TEST_LUMIERE live-gateway",
            "city": "Barcelona",
            "language": "en",
            "duration_days": 2,
        }
        r = sess.post(f"{BASE_URL}/api/experiences", json=payload, timeout=30)
        assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
        data = r.json()
        eid = data.get("id") or data.get("_id") or data.get("experience_id")
        assert eid, f"no experience id in {data}"
        return eid

    def test_plan_via_live_gateway(self, s, exp_id):
        t0 = time.time()
        r = s.post(
            f"{BASE_URL}/api/experiences/{exp_id}/plan",
            json={"intent": "A romantic 2-day Barcelona trip with Gaudí, tapas, and golden hour photography."},
            timeout=180,
        )
        elapsed = time.time() - t0
        print(f"/plan elapsed={elapsed:.1f}s status={r.status_code}")
        assert r.status_code == 200, f"plan failed: {r.status_code} {r.text[:1000]}"
        plan = r.json()

        # Bilingual title
        title = plan.get("title") or plan.get("plan", {}).get("title")
        assert title, f"no plan.title in {plan}"
        assert isinstance(title, dict) and "en" in title and "es" in title, f"title not bilingual: {title}"
        assert title["en"] and title["es"], f"empty title parts: {title}"

        # Beats non-empty
        beats = plan.get("beats") or plan.get("plan", {}).get("beats") or []
        assert isinstance(beats, list) and len(beats) > 0, f"beats empty: {beats}"

        # Missions non-empty
        m = plan.get("missions") or plan.get("plan", {}).get("missions") or []
        if isinstance(m, dict):
            m = m.get("missions", [])
        assert isinstance(m, list) and len(m) > 0, f"missions empty: {m}"
        print(f"plan OK: title.en='{title['en'][:60]}' beats={len(beats)} missions={len(m)}")

    def test_trace_provenance(self, s, exp_id):
        r = s.get(f"{BASE_URL}/api/experiences/{exp_id}/agent-runs", timeout=30)
        assert r.status_code == 200, r.text
        runs = r.json()
        # Normalize to list
        if isinstance(runs, dict):
            runs = runs.get("runs") or runs.get("agent_runs") or list(runs.values())
        assert isinstance(runs, list) and len(runs) > 0, f"no runs: {runs}"

        by_agent = {}
        for run in runs:
            key = run.get("agent") or run.get("name") or run.get("role") or ""
            by_agent.setdefault(key, []).append(run)
        print("agent run keys:", list(by_agent.keys()))

        def find(substr):
            for k, v in by_agent.items():
                if substr in k.lower():
                    return v[-1]
            return None

        director = find("director")
        cinema = find("cinema")
        context = find("context")

        assert director, f"no director run in {list(by_agent.keys())}"
        assert cinema, f"no cinematographer run in {list(by_agent.keys())}"

        for name, run in (("director", director), ("cinematographer", cinema)):
            assert run.get("service") == "vertex-agent-engine", f"{name} service={run.get('service')}"
            assert run.get("status") == "ok", f"{name} status={run.get('status')} run={run}"
            assert run.get("model") == "agent-engine", f"{name} model={run.get('model')}"
            lat = run.get("latency_ms") or 0
            assert lat > 0, f"{name} latency_ms={lat}"
            print(f"{name}: service={run['service']} status={run['status']} latency={lat}ms")

        if context:
            # Parallel not connected — expected
            assert context.get("service") == "parallel", f"context service={context.get('service')}"
            assert context.get("status") == "not_connected", f"context status={context.get('status')}"
            print(f"context: service=parallel status=not_connected (expected)")

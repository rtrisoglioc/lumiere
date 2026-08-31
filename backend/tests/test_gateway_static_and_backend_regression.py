"""Static AST verification of gateway/server.py and regression tests
for the serving Emergent backend (which does NOT import gateway/)."""
import ast
import os
import py_compile
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lumiere-studio-7.preview.emergentagent.com").rstrip("/")
GATEWAY_FILE = "/app/gateway/server.py"
BEARER = "e2e_1788105676"


# ---------- Static AST verification of gateway/server.py ----------
class TestGatewayStatic:
    @pytest.fixture(scope="class")
    def source(self):
        with open(GATEWAY_FILE, "r") as f:
            return f.read()

    @pytest.fixture(scope="class")
    def tree(self, source):
        return ast.parse(source)

    def test_py_compile(self):
        py_compile.compile(GATEWAY_FILE, doraise=True)

    def test_ast_parse(self, tree):
        assert isinstance(tree, ast.Module)

    def test_helpers_exist(self, tree):
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for name in ("_query", "_to_jsonable", "_session_id"):
            assert name in funcs, f"missing helper {name}"

    def test_query_does_not_call_dot_query(self, source):
        # _query body should not call `a.query(` or `.query(` on the agent
        tree = ast.parse(source)
        query_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_query")
        for node in ast.walk(query_fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "query", "_query still calls .query()"

    def test_query_uses_stream_query_and_sessions(self, source):
        tree = ast.parse(source)
        query_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_query")
        attrs = [n.func.attr for n in ast.walk(query_fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        assert "stream_query" in attrs
        assert "create_session" in attrs
        assert "get_session" in attrs

    def test_query_returns_session_id_and_events_dict(self, source):
        tree = ast.parse(source)
        query_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_query")
        returns = [n for n in ast.walk(query_fn) if isinstance(n, ast.Return)]
        assert returns, "_query has no return"
        ret_val = returns[-1].value
        assert isinstance(ret_val, ast.Dict), "_query must return a dict literal"
        keys = {k.value for k in ret_val.keys if isinstance(k, ast.Constant)}
        assert {"session_id", "events"}.issubset(keys), f"missing keys, got {keys}"

    def test_agent_and_vision_call_query(self, source):
        tree = ast.parse(source)
        for fname in ("run_agent", "run_vision"):
            fn = next(n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname)
            calls = [n.func.id for n in ast.walk(fn)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
            assert "_query" in calls, f"{fname} does not call _query"


# ---------- Regression tests: serving Emergent backend ----------
class TestServingBackendRegression:
    @pytest.fixture(scope="class")
    def s(self):
        sess = requests.Session()
        sess.headers.update({"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json"})
        return sess

    def test_agent_health(self, s):
        r = s.get(f"{BASE_URL}/api/agent/health", timeout=15)
        assert r.status_code == 200, r.text

    def test_partner_health(self, s):
        r = s.get(f"{BASE_URL}/api/partner/health", timeout=15)
        assert r.status_code == 200, r.text

    def test_auth_me(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)

    def test_experience_and_plan(self, s):
        payload = {
            "title": "TEST_LUMIERE regression",
            "city": "Paris",
            "language": "en",
            "duration_days": 2,
        }
        r = s.post(f"{BASE_URL}/api/experiences", json=payload, timeout=30)
        assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
        exp = r.json()
        exp_id = exp.get("id") or exp.get("_id") or exp.get("experience_id")
        assert exp_id, f"no experience id in {exp}"

        r2 = s.post(f"{BASE_URL}/api/experiences/{exp_id}/plan",
                    json={"intent": "A romantic 2-day Paris trip with art, food, and photography."},
                    timeout=60)
        assert r2.status_code == 200, f"plan failed: {r2.status_code} {r2.text}"
        plan = r2.json()
        # Bilingual title
        title = plan.get("title") or plan.get("plan", {}).get("title")
        assert title, f"no plan.title in {plan}"
        assert isinstance(title, dict) and "en" in title and "es" in title, f"title not bilingual: {title}"
        # Missions non-empty (may be wrapped as {"missions": [...]})
        m = plan.get("missions") or plan.get("plan", {}).get("missions") or []
        if isinstance(m, dict):
            m = m.get("missions", [])
        assert isinstance(m, list) and len(m) > 0, f"missions empty: {m}"

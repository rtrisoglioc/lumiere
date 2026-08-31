"""Agentic orchestration adapter.

Routes each agent run to the best available runtime:
  1. Google Cloud Vertex AI Agent Engine (Agent Builder) — when an engine id +
     credentials are configured (service="vertex-agent-engine").
  2. Google Cloud Vertex AI Gemini direct — when GCP credentials are present
     (service="vertex-ai").
  3. Emergent Gemini proxy — dev-only fallback (service="emergent-proxy").

All AI reasoning is Google Gemini. No other AI providers are used at runtime.
The production Google Cloud path (1/2) activates automatically once secrets are
set; no code change required.
"""
import os
import re
import json
import time
import asyncio

import vertex_gemini_adapter as vertex

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
PROXY_FAST = "gemini-3.5-flash"
PROXY_PRO = "gemini-3.1-pro-preview"

GATEWAY_URL = (os.environ.get("LUMIERE_GATEWAY_URL") or "").strip().rstrip("/")
GATEWAY_TOKEN = os.environ.get("LUMIERE_GATEWAY_TOKEN", "")


def gateway_enabled() -> bool:
    return bool(GATEWAY_URL)


class AgentBuilderAdapter:
    provider = "google"

    def status(self) -> dict:
        v = vertex.status()
        if v["connected"] and v["agent_engine_configured"]:
            backend, service, connected = "vertex-agent-engine", "vertex-agent-engine", True
        elif v["connected"]:
            backend, service, connected = "vertex-ai", "vertex-ai", True
        else:
            backend, service, connected = "emergent-proxy", "emergent-proxy", False
        return {
            "orchestration_backend": backend,
            "service": service,
            "agent_builder_connected": bool(v["connected"] and v["agent_engine_configured"]),
            "vertex_connected": v["connected"],
            "provider": "google",
            "model": PROXY_PRO if not connected else (vertex.VERTEX_PRO),
            "project": v.get("project"),
            "location": v.get("location"),
            "note_en": ("Real Gemini via Google Cloud Vertex AI." if v["connected"]
                        else "DEV fallback: Gemini via Emergent proxy. Set GOOGLE_APPLICATION_CREDENTIALS_JSON to activate Vertex AI."),
            "note_es": ("Gemini real vía Google Cloud Vertex AI." if v["connected"]
                        else "Fallback DEV: Gemini vía proxy Emergent. Define GOOGLE_APPLICATION_CREDENTIALS_JSON para activar Vertex AI."),
        }

    async def run(self, agent, session_id, system, prompt, files=None, expect_json=True, model=None, operation="reason"):
        started = time.time()
        want_fast = (model == PROXY_FAST)
        status = "ok"
        try:
            if gateway_enabled():
                raw, used_model = await asyncio.to_thread(
                    self._gateway, operation, system, prompt, files, session_id)
                service, backend, connected = "vertex-agent-engine", "vertex-agent-engine", True
            elif vertex.is_connected():
                use_engine = vertex.has_agent_engine() and not files  # engine for text reasoning
                if use_engine:
                    raw = await asyncio.to_thread(vertex.agent_engine_query, f"{system}\n\n{prompt}")
                    raw = raw if isinstance(raw, str) else json.dumps(raw)
                    used_model, service, backend = f"agent-engine:{vertex.AGENT_ENGINE_ID}", "vertex-agent-engine", "vertex-agent-engine"
                else:
                    raw, used_model = await asyncio.to_thread(vertex.generate, system, prompt, files, want_fast)
                    service, backend = "vertex-ai", "vertex-ai"
                connected = True
            else:
                raw, used_model = await self._emergent(session_id, system, prompt, files, want_fast)
                service, backend, connected = "emergent-proxy", "emergent-proxy", False
        except Exception as e:
            status = "error"
            raw, used_model, service, backend, connected = (
                json.dumps({"_error": str(e)[:300], "confidence": 0.0}), "error", "error", "error", False)

        latency_ms = int((time.time() - started) * 1000)
        parsed = raw
        confidence = None
        if expect_json:
            parsed = _extract_json(raw)
            if isinstance(parsed, dict):
                confidence = parsed.get("confidence")
        meta = {
            "agent": agent,
            "orchestration_backend": backend,
            "service": service,
            "operation": operation,
            "status": status,
            "agent_builder_connected": backend == "vertex-agent-engine",
            "vertex_connected": connected,
            "provider": "google",
            "model": used_model,
            "latency_ms": latency_ms,
            "confidence": confidence if confidence is not None else 0.72,
        }
        return parsed, meta

    async def _emergent(self, session_id, system, prompt, files, want_fast):
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        model = PROXY_FAST if want_fast else PROXY_PRO
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=system).with_model("gemini", model)
        file_contents = None
        if files:
            file_contents = [FileContentWithMimeType(file_path=f["path"], mime_type=f["mime"]) for f in files]
        message = UserMessage(text=prompt, file_contents=file_contents) if file_contents else UserMessage(text=prompt)
        raw = await chat.send_message(message)
        return raw, model

    def _gateway(self, operation, system, prompt, files, session_id):
        import requests
        headers = {"Authorization": f"Bearer {GATEWAY_TOKEN}"}
        if files:
            f = files[0]
            with open(f["path"], "rb") as fh:
                resp = requests.post(
                    f"{GATEWAY_URL}/vision", headers=headers, timeout=(30, 600),
                    data={"operation": operation, "session_id": "",
                          "payload": json.dumps({"system": system, "prompt": prompt})},
                    files={"file": (os.path.basename(f["path"]), fh, f["mime"])},
                )
        else:
            resp = requests.post(
                f"{GATEWAY_URL}/agent", headers={**headers, "Content-Type": "application/json"},
                timeout=(30, 300), json={"operation": operation, "session_id": None,
                                         "user_id": "lumiere",
                                         "payload": {"system": system, "prompt": prompt}})
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")
        if isinstance(result, dict) and "events" in result:
            raw = _best_json_from_events(result["events"]) or json.dumps(result)
        else:
            raw = result if isinstance(result, str) else json.dumps(result)
        return raw, data.get("model", "agent-engine")


def gateway_context(objective, queries, session_id=None):
    """Run the ADK CONTEXT sub-agent via the Cloud Run gateway. The Agent Engine
    executes the parallel_search tool using ITS OWN PARALLEL_API_KEY (no Parallel
    key needed on Emergent). Returns a context dict compatible with agents._context_text."""
    import requests
    started = time.time()
    system = ("You are CONTEXT. Call the parallel_search tool with the provided objective and queries, "
              "then summarize the real evidence into a compact bilingual context brief.")
    prompt = (f"objective={objective!r}\nqueries={json.dumps(queries)}\n"
              "Call parallel_search(objective=objective, queries=queries) now, then return the brief.")
    resp = requests.post(
        f"{GATEWAY_URL}/agent",
        headers={"Authorization": f"Bearer {GATEWAY_TOKEN}", "Content-Type": "application/json"},
        timeout=(30, 300),
        json={"operation": "context", "session_id": None, "user_id": "lumiere",
              "payload": {"system": system, "prompt": prompt, "objective": objective, "queries": queries}})
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result") or {}
    events = result.get("events") if isinstance(result, dict) else []
    parsed = _parse_context_events(events or [])
    parsed["objective"] = objective
    parsed["queries"] = queries
    parsed["latency_ms"] = int((time.time() - started) * 1000)
    return parsed


def _parse_context_events(events):
    """Extract the parallel_search tool response (real sources) from ADK events."""
    sources, tool_status = [], None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        content = ev.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue
        for p in parts:
            if not isinstance(p, dict):
                continue
            fr = p.get("function_response") or p.get("functionResponse")
            if not isinstance(fr, dict) or fr.get("name") != "parallel_search":
                continue
            r = fr.get("response") or {}
            if "results" not in r and isinstance(r.get("result"), dict):
                r = r["result"]
            tool_status = r.get("status") or tool_status
            for it in (r.get("results") or [])[:8]:
                if isinstance(it, dict):
                    sources.append({"title": it.get("title"), "url": it.get("url"),
                                    "excerpts": it.get("excerpts") or []})
    ok = bool(sources) and tool_status == "ok"
    return {"ok": ok, "connected": True,
            "status": tool_status or ("ok" if sources else "not_connected"),
            "results": sources, "brief_raw": _best_json_from_events(events)}


def _event_texts(events):
    out = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        content = ev.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue
        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        if texts:
            out.append("\n".join(texts))
    return out


def _best_json_from_events(events):
    """Pick the event text that parses to a valid JSON object (final complete
    event preferred), tolerating streaming partials/transfer events."""
    texts = _event_texts(events)
    candidates = list(reversed(texts)) + ["".join(texts)]
    for c in candidates:
        parsed = _extract_json(c)
        if isinstance(parsed, dict) and not parsed.get("_parse_error"):
            return c
    return (texts[-1] if texts else "")


def _extract_json(text):
    if not isinstance(text, str):
        return text
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return {"_raw": text, "confidence": 0.4, "_parse_error": True}


agent_builder = AgentBuilderAdapter()

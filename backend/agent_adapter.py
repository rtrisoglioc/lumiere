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
            if vertex.is_connected():
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

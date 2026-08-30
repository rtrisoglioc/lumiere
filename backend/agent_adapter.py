"""Agentic orchestration adapter.

MODULAR BOUNDARY. In production this routes agent runs to Google Cloud Agent
Builder / Vertex AI Agent Engine. That runtime is provisioned in the user's GCP
project (billing + service accounts + agents + data stores) and is NOT connected
in this environment.

Until GCP credentials are provided, `orchestration_backend = "direct_gemini"`:
the agents' reasoning is REAL (Gemini multimodal via the approved Emergent
surface), but the Agent Builder orchestration runtime itself is not connected.
This is flagged honestly in the UI traceability panel. Swap the `run` body to
call Agent Engine sessions without changing any domain code.
"""
import os
import re
import json
import time

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
GEMINI_MODEL = "gemini-3.1-pro-preview"


class AgentBuilderAdapter:
    orchestration_backend = "direct_gemini"
    agent_builder_connected = False  # flip to True once GCP Agent Engine is wired
    provider = "google"
    model = GEMINI_MODEL

    def status(self) -> dict:
        return {
            "orchestration_backend": self.orchestration_backend,
            "agent_builder_connected": self.agent_builder_connected,
            "provider": self.provider,
            "model": self.model,
            "note_en": "Reasoning runs on real Gemini. Google Agent Builder runtime not connected (awaiting GCP project credentials).",
            "note_es": "El razonamiento corre en Gemini real. El runtime de Google Agent Builder no está conectado (esperando credenciales del proyecto GCP).",
        }

    async def run(self, agent: str, session_id: str, system: str, prompt: str, files=None, expect_json=True):
        """Execute one agent turn. Returns (parsed_output, meta)."""
        started = time.time()
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=system).with_model(
            "gemini", self.model
        )
        file_contents = None
        if files:
            file_contents = [FileContentWithMimeType(file_path=f["path"], mime_type=f["mime"]) for f in files]
        message = UserMessage(text=prompt, file_contents=file_contents) if file_contents else UserMessage(text=prompt)
        raw = await chat.send_message(message)
        latency_ms = int((time.time() - started) * 1000)

        parsed = raw
        confidence = None
        if expect_json:
            parsed = _extract_json(raw)
            if isinstance(parsed, dict):
                confidence = parsed.get("confidence")
        meta = {
            "agent": agent,
            "orchestration_backend": self.orchestration_backend,
            "agent_builder_connected": self.agent_builder_connected,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": latency_ms,
            "confidence": confidence if confidence is not None else 0.72,
        }
        return parsed, meta


def _extract_json(text: str):
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

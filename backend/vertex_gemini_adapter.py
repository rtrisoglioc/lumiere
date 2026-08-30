"""Google Cloud Vertex AI (Gemini + Agent Engine) adapter.

Production-ready. Activates automatically once GOOGLE_APPLICATION_CREDENTIALS_JSON
+ GOOGLE_CLOUD_PROJECT are present in the runtime environment (set via the deploy
platform's secret manager — never committed). Until then it reports not_connected
and callers fall back to the dev reasoning path. Imports are lazy so the module
never breaks the app when the SDK/creds are absent.

AI provider: Google only (Gemini via Vertex AI). No other AI providers.
"""
import os
import json
import tempfile

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("VERTEX_AGENT_ENGINE_ID")
SCOPE = "https://www.googleapis.com/auth/cloud-platform"

# Map internal model aliases to Vertex-available model ids.
VERTEX_FAST = "gemini-2.5-flash"
VERTEX_PRO = "gemini-2.5-pro"

_client = None


def _has_creds() -> bool:
    return bool((os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip() and PROJECT)


def is_connected() -> bool:
    if not _has_creds():
        return False
    try:
        import google.genai  # noqa: F401
        return True
    except Exception:
        return False


def has_agent_engine() -> bool:
    return bool((AGENT_ENGINE_ID or "").strip())


def _get_client():
    global _client
    if _client is not None:
        return _client
    from google import genai
    from google.oauth2 import service_account

    info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    credentials = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
    _client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION, credentials=credentials)
    return _client


def _resource_name(value: str) -> str:
    if value.startswith("projects/"):
        return value
    return f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{value}"


def generate(system: str, prompt: str, files=None, want_fast: bool = False) -> str:
    """Real Gemini call via Vertex AI. Returns raw text (expected JSON)."""
    from google.genai import types

    client = _get_client()
    parts = []
    if files:
        for f in files:
            with open(f["path"], "rb") as fh:
                parts.append(types.Part.from_bytes(data=fh.read(), mime_type=f["mime"]))
    parts.append(types.Part.from_text(text=prompt))

    model = VERTEX_FAST if want_fast else VERTEX_PRO
    resp = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    return resp.text, model


def agent_engine_query(prompt: str):
    """Invoke a deployed Vertex Agent Engine (Agent Builder) if configured."""
    client = _get_client()
    agent = client.agent_engines.get(name=_resource_name(AGENT_ENGINE_ID))
    return agent.query(input=prompt)


def status() -> dict:
    connected = is_connected()
    return {
        "connected": connected,
        "provider": "google",
        "surface": "vertex-ai",
        "project": PROJECT if connected else None,
        "location": LOCATION,
        "agent_engine_configured": has_agent_engine(),
    }

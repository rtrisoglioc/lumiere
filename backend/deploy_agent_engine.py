"""One-off deployment of the LUMIÈRE ADK orchestrator to Vertex AI Agent Engine.

NOT run automatically and NOT part of the serving backend. Executes ONLY when
real GCP credentials are present. It creates a single `reasoningEngine` resource
and prints its resource name, which you then store in the VERTEX_AGENT_ENGINE_ID
secret.

Run (Phase B-2, with credentials available in the environment):
    python -m deploy_agent_engine

Required env: GOOGLE_APPLICATION_CREDENTIALS_JSON, GOOGLE_CLOUD_PROJECT,
GOOGLE_CLOUD_LOCATION, GCS_STAGING_BUCKET (gs://...).
Deploy deps: backend/adk_app/requirements-deploy.txt (google-adk, aiplatform[adk,agent_engines], google-genai).
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "lumiere-agentic-cinema")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET = os.environ.get("GCS_STAGING_BUCKET") or f"gs://{PROJECT}-agent-staging-{LOCATION}"


def _ensure_adc():
    raw = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip()
    if not raw:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS_JSON not set. Provide the service-account JSON "
              "via the Secrets manager (or backend/.env, git-ignored) before deploying. Nothing deployed.")
        sys.exit(1)
    fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
    fd.write(raw)
    fd.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fd.name


def main():
    _ensure_adc()
    import vertexai
    from vertexai import agent_engines
    from adk_app.agent import root_agent

    reqs = [line.strip() for line in
            (Path(__file__).parent / "adk_app" / "requirements-deploy.txt").read_text().splitlines()
            if line.strip()]

    print(f"Deploying LUMIÈRE orchestrator to Agent Engine — project={PROJECT} location={LOCATION} bucket={BUCKET}")
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=BUCKET)
    app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)
    remote = agent_engines.create(
        agent_engine=app,
        display_name="LUMIERE Cinema Orchestrator",
        requirements=reqs,
    )
    name = remote.api_resource.name
    print("\n=== DEPLOYED ===")
    print("REASONING_ENGINE_NAME =", name)
    print("Store this as the secret VERTEX_AGENT_ENGINE_ID, then redeploy the app.")


if __name__ == "__main__":
    main()

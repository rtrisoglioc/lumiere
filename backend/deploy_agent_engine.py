"""One-off deployment of the LUMIÈRE ADK orchestrator to Vertex AI Agent Engine.

Run from Cloud Shell with KEYLESS auth (Application Default Credentials via
`gcloud auth application-default login`). No service-account JSON key is created
or required. If GOOGLE_APPLICATION_CREDENTIALS_JSON happens to be present it is
used, but ADC is the primary path. NOT part of the serving backend.

Usage (Cloud Shell):
    pip install -r adk_app/requirements-deploy.txt
    export GOOGLE_CLOUD_PROJECT=lumiere-agentic-cinema GOOGLE_CLOUD_LOCATION=us-central1
    export GCS_STAGING_BUCKET=gs://lumiere-agentic-cinema-agent-staging-us-central1
    export GCS_BUCKET=lumiere-agentic-cinema-media
    export PARALLEL_API_KEY=...        # only in the shell; goes into the engine env
    python -m deploy_agent_engine
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
MEDIA = os.environ.get("GCS_BUCKET", "lumiere-agentic-cinema-media")


def _maybe_json_adc():
    raw = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip()
    if raw and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        fd = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        fd.write(raw); fd.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fd.name


def main():
    os.chdir(Path(__file__).parent)
    _maybe_json_adc()  # optional; ADC (gcloud auth application-default login) is the default keyless path
    import vertexai
    from vertexai import agent_engines
    from adk_app.agent import root_agent

    reqs = [l.strip() for l in (Path(__file__).parent / "adk_app" / "requirements-deploy.txt").read_text().splitlines() if l.strip()]
    engine_env = {
        "GOOGLE_CLOUD_PROJECT": PROJECT,
        "GOOGLE_CLOUD_LOCATION": LOCATION,
        "GCS_BUCKET": MEDIA,
    }
    if os.environ.get("PARALLEL_API_KEY"):
        engine_env["PARALLEL_API_KEY"] = os.environ["PARALLEL_API_KEY"]
    if os.environ.get("PARALLEL_MODE"):
        engine_env["PARALLEL_MODE"] = os.environ["PARALLEL_MODE"]

    print(f"Deploying LUMIÈRE orchestrator — project={PROJECT} location={LOCATION} staging={BUCKET}")
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=BUCKET)
    app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)
    remote = agent_engines.create(
        agent_engine=app,
        display_name="LUMIERE Cinema Orchestrator",
        requirements=reqs,
        extra_packages=["adk_app"],
        env_vars=engine_env,
    )
    name = remote.api_resource.name
    print("\n=== DEPLOYED ===")
    print("REASONING_ENGINE_NAME =", name)
    print("Set this as VERTEX_AGENT_ENGINE_ID for the Cloud Run gateway.")


if __name__ == "__main__":
    main()

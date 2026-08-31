"""LUMIÈRE Agent Gateway — runs on Google Cloud Run with the attached service
account (keyless ADC). It is the ONLY component that talks to Vertex AI Agent
Engine / Gemini and Google Cloud Storage. The Emergent app calls it over HTTPS
with a shared bearer token (LUMIERE_GATEWAY_TOKEN).

No service-account JSON key: authentication is Application Default Credentials
provided by the attached Cloud Run service account.
"""
import os
import json
import uuid
import tempfile

import vertexai
from vertexai import agent_engines
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
ENGINE = os.environ["VERTEX_AGENT_ENGINE_ID"]
GCS_BUCKET = os.environ.get("GCS_BUCKET")
TOKEN = os.environ.get("LUMIERE_GATEWAY_TOKEN", "")

vertexai.init(project=PROJECT, location=LOCATION)
_agent = None


def agent():
    global _agent
    if _agent is None:
        _agent = agent_engines.get(ENGINE)
    return _agent


app = FastAPI(title="LUMIERE Agent Gateway")


def _auth(authorization):
    if not TOKEN or authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


def _query(operation, payload, session_id, user_id="lumiere"):
    message = json.dumps({"operation": operation, "payload": payload})
    sid = session_id or f"s_{uuid.uuid4().hex[:12]}"
    result = agent().query(user_id=user_id, session_id=sid, message=message)
    return result


def _upload_gcs(local_path, dest, content_type):
    from google.cloud import storage
    client = storage.Client(project=PROJECT)
    blob = client.bucket(GCS_BUCKET).blob(dest)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{GCS_BUCKET}/{dest}"


class AgentIn(BaseModel):
    operation: str
    payload: dict = {}
    session_id: str | None = None
    user_id: str | None = None


@app.get("/healthz")
def healthz():
    return {"ok": True, "project": PROJECT, "location": LOCATION, "engine": ENGINE, "bucket": GCS_BUCKET}


@app.post("/agent")
def run_agent(body: AgentIn, authorization: str = Header(default=None)):
    _auth(authorization)
    try:
        result = _query(body.operation, body.payload, body.session_id, body.user_id or "lumiere")
        return {"result": result, "model": "agent-engine"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"agent_engine_error: {str(e)[:400]}")


@app.post("/vision")
async def run_vision(file: UploadFile = File(...), operation: str = Form("footage_analysis"),
                     payload: str = Form("{}"), session_id: str = Form(None),
                     authorization: str = Header(default=None)):
    _auth(authorization)
    try:
        data = await file.read()
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "mp4"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        tmp.write(data); tmp.close()
        dest = f"vision/{uuid.uuid4().hex}.{ext}"
        gcs_uri = _upload_gcs(tmp.name, dest, file.content_type or "video/mp4")
        pl = json.loads(payload or "{}")
        pl["gcs_uri"] = gcs_uri
        pl["mime_type"] = file.content_type or "video/mp4"
        result = _query(operation, pl, session_id)
        return {"result": result, "model": "agent-engine", "gcs_uri": gcs_uri}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"vision_error: {str(e)[:400]}")

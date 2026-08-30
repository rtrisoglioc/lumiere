"""GCS media bridge for the Vision path (prepared in Phase B-1, wired in B-2).

Uploads original footage to a project-owned GCS bucket and returns a gs:// URI so
the deployed Vision sub-agent can analyze it via Vertex multimodal — keeping clear
Google Cloud provenance. Lazy imports + graceful not_configured so it never
affects the current golden path until enabled.
"""
import os
import json
import tempfile

GCS_BUCKET = (os.environ.get("GCS_BUCKET") or "").strip()  # e.g. lumiere-agentic-cinema-media
SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_client = None


def is_configured() -> bool:
    if not GCS_BUCKET or not (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip():
        return False
    try:
        import google.cloud.storage  # noqa: F401
        return True
    except Exception:
        return False


def _get_client():
    global _client
    if _client is not None:
        return _client
    from google.cloud import storage
    from google.oauth2 import service_account
    info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
    _client = storage.Client(project=info.get("project_id"), credentials=creds)
    return _client


def upload_media(local_path: str, dest_path: str, content_type: str) -> str:
    """Upload a local file to gs://GCS_BUCKET/dest_path and return the gs:// URI."""
    client = _get_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path, content_type=content_type)
    return f"gs://{GCS_BUCKET}/{dest_path}"


def status() -> dict:
    return {"configured": is_configured(), "bucket": GCS_BUCKET or None}

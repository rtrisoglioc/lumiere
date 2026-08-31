"""Vertex AI (Veo) video generation via the Cloud Run gateway.

Emergent has NO Google credentials. All Veo calls go through the keyless-ADC
Cloud Run gateway (LUMIERE_GATEWAY_URL) exactly like /agent. Veo is long-running:
submit() returns an operation_name, poll() checks it, download() streams the mp4.
When the gateway is not configured this reports not_connected (no mock output)."""
import os
import requests

GATEWAY_URL = (os.environ.get("LUMIERE_GATEWAY_URL") or "").strip().rstrip("/")
GATEWAY_TOKEN = os.environ.get("LUMIERE_GATEWAY_TOKEN", "")
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.0-generate-001")


def _headers():
    return {"Authorization": f"Bearer {GATEWAY_TOKEN}", "Content-Type": "application/json"}


class VertexVideoAdapter:
    provider = "google_vertex_veo"

    @property
    def connected(self) -> bool:
        return bool(GATEWAY_URL)

    def status(self) -> dict:
        c = self.connected
        return {
            "connected": c,
            "provider": self.provider,
            "model": VEO_MODEL,
            "status": "connected" if c else "not_connected",
            "note_en": ("Vertex AI (Veo) via Cloud Run gateway (keyless ADC)." if c
                        else "Vertex AI (Veo) not connected — set LUMIERE_GATEWAY_URL."),
            "note_es": ("Vertex AI (Veo) vía gateway de Cloud Run (ADC sin clave)." if c
                        else "Vertex AI (Veo) sin conectar — define LUMIERE_GATEWAY_URL."),
        }

    def submit(self, prompt: str, options: dict) -> dict:
        if not self.connected:
            return {"ok": False, "status": "not_connected"}
        resp = requests.post(
            f"{GATEWAY_URL}/video", headers=_headers(), timeout=(30, 120),
            json={"prompt": prompt, "aspect_ratio": options.get("aspect_ratio", "16:9"),
                  "duration_sec": options.get("duration_sec", 8)})
        resp.raise_for_status()
        return {"ok": True, **resp.json()}

    def poll(self, operation_name: str) -> dict:
        resp = requests.post(
            f"{GATEWAY_URL}/video/status", headers=_headers(), timeout=(30, 120),
            json={"operation_name": operation_name})
        resp.raise_for_status()
        return resp.json()

    def download(self, gcs_uri: str):
        resp = requests.get(
            f"{GATEWAY_URL}/video/download", headers={"Authorization": f"Bearer {GATEWAY_TOKEN}"},
            params={"gcs_uri": gcs_uri}, timeout=(30, 300))
        resp.raise_for_status()
        return resp.content


vertex_video = VertexVideoAdapter()

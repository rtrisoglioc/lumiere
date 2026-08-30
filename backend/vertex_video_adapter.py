"""Vertex AI (Veo) video generation/enhancement adapter.

MODULAR BOUNDARY. In production this calls Google Cloud Vertex AI (Veo) to
generate video from a prompt and to AI-enhance/edit the user's own videos. That
runtime is provisioned in the user's GCP project (billing + service account +
Vertex AI API). It is NOT connected in this environment.

Per the user's decision, the interface is ready but returns a clearly-marked
"not_connected" mock. Swap `generate` / `enhance` bodies to call Vertex once GCP
credentials are available — no domain/UI changes required.
"""
from db import now_iso


class VertexVideoAdapter:
    connected = False
    provider = "google_vertex_veo"

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "provider": self.provider,
            "status": "not_connected",
            "note_en": "Vertex AI (Veo) not connected — awaiting GCP project credentials. UI flow is ready.",
            "note_es": "Vertex AI (Veo) sin conectar — esperando credenciales del proyecto GCP. El flujo de UI está listo.",
        }

    def generate(self, prompt: str, options: dict) -> dict:
        return {
            "ok": False,
            "mock": True,
            "status": "not_connected",
            "prompt": prompt,
            "options": options,
            "message_en": "Veo generation will run here once Vertex AI is connected.",
            "message_es": "La generación con Veo correrá aquí una vez conectado Vertex AI.",
            "requested_at": now_iso(),
        }

    def enhance(self, asset_ref: str, options: dict) -> dict:
        return {
            "ok": False,
            "mock": True,
            "status": "not_connected",
            "asset": asset_ref,
            "options": options,
            "message_en": "AI enhancement will run on Vertex AI (Veo) once connected.",
            "message_es": "La mejora con IA correrá en Vertex AI (Veo) una vez conectado.",
            "requested_at": now_iso(),
        }


vertex_video = VertexVideoAdapter()

"""Hackathon PartnerAdapter.

MODULAR BOUNDARY + HARD BLOCKER. The partner track (IBM / Grafana Labs /
Parallel / ClickHouse / Replit) is NOT selected yet, so there is NO real
integration. This is a clearly-marked MOCK exposing the exact interface the real
adapter must implement: health_check, execute_workflow_capability,
evidence_payload, error_mapping. Nothing here fabricates real partner behavior.
"""
from db import now_iso

SELECTED_TRACK = None  # set to "ibm" | "grafana" | "parallel" | "clickhouse" | "replit"


class PartnerAdapter:
    connected = False

    def health_check(self) -> dict:
        return {
            "connected": self.connected,
            "selected_track": SELECTED_TRACK,
            "status": "not_connected",
            "message_en": "Partner track not selected. Interface ready; no real integration wired (mock).",
            "message_es": "Track de partner sin seleccionar. Interfaz lista; sin integración real (mock).",
            "checked_at": now_iso(),
        }

    def execute_workflow_capability(self, capability: str, payload: dict) -> dict:
        return {
            "ok": False,
            "mock": True,
            "capability": capability,
            "reason_en": "Partner not connected — select a track to enable this capability.",
            "reason_es": "Partner no conectado — selecciona un track para habilitar esta capacidad.",
            "echo": payload,
        }

    def evidence_payload(self) -> dict:
        return {
            "mock": True,
            "selected_track": SELECTED_TRACK,
            "evidence": [],
            "note_en": "No partner evidence yet (mock).",
            "note_es": "Aún no hay evidencia del partner (mock).",
        }

    def error_mapping(self, code: str) -> dict:
        return {"code": code, "mapped": "partner_not_connected", "retryable": False}


partner = PartnerAdapter()

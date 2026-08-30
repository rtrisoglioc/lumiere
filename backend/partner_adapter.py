"""Hackathon PartnerAdapter — Parallel (Search API).

Production adapter for the selected Partner track: **Parallel**. It makes a REAL
runtime call to the Parallel Search API (POST https://api.parallel.ai/v1/search,
header `x-api-key`) and its results feed the Context Agent, materially influencing
Story Plan / Shot Missions.

Activates automatically once PARALLEL_API_KEY is present (set via secret manager).
Until then health_check reports not_connected and search() returns a clearly
not_connected result — no fabricated partner data.

Interface: health_check, execute_workflow_capability, evidence_payload, error_mapping.
"""
import os
import requests

from db import now_iso

PARALLEL_URL = "https://api.parallel.ai/v1/search"
SELECTED_TRACK = "parallel"


class PartnerAdapter:
    track = SELECTED_TRACK

    def _key(self):
        return (os.environ.get("PARALLEL_API_KEY") or "").strip()

    @property
    def connected(self) -> bool:
        return bool(self._key())

    def health_check(self) -> dict:
        connected = self.connected
        return {
            "connected": connected,
            "selected_track": self.track,
            "product": "Parallel Search API",
            "status": "connected" if connected else "not_connected",
            "endpoint": PARALLEL_URL,
            "message_en": ("Parallel Search API connected — called at runtime by the Context Agent."
                           if connected else "Parallel not connected. Set PARALLEL_API_KEY secret to activate."),
            "message_es": ("Parallel Search API conectado — llamado en runtime por el Context Agent."
                           if connected else "Parallel sin conectar. Define el secreto PARALLEL_API_KEY para activar."),
            "checked_at": now_iso(),
        }

    def search(self, objective: str, queries: list, mode: str = None, max_chars_total: int = 40000) -> dict:
        """Real Parallel Search API call. Returns normalized results + evidence."""
        if not self.connected:
            return {"ok": False, "connected": False, "status": "not_connected",
                    "reason_en": "Parallel not connected — set PARALLEL_API_KEY.",
                    "reason_es": "Parallel sin conectar — define PARALLEL_API_KEY.",
                    "objective": objective, "queries": queries, "results": []}
        body = {
            "objective": objective,
            "search_queries": queries[:5],
            "mode": mode or os.environ.get("PARALLEL_MODE", "base"),
            "max_chars_total": max_chars_total,
        }
        try:
            resp = requests.post(
                PARALLEL_URL,
                headers={"x-api-key": self._key(), "Content-Type": "application/json"},
                json=body, timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in (data.get("results") or [])[:8]:
                excerpts = r.get("excerpts") or []
                if isinstance(excerpts, list):
                    excerpts = [str(e)[:600] for e in excerpts][:3]
                results.append({"title": r.get("title"), "url": r.get("url"), "excerpts": excerpts})
            return {"ok": True, "connected": True, "status": "ok", "objective": objective,
                    "queries": body["search_queries"], "mode": body["mode"], "results": results}
        except Exception as e:
            return {"ok": False, "connected": True, "status": "error",
                    "error": str(e)[:300], "objective": objective, "queries": queries, "results": []}

    def execute_workflow_capability(self, capability: str, payload: dict) -> dict:
        if capability == "context_search":
            return self.search(payload.get("objective", ""), payload.get("queries", []))
        return {"ok": False, "capability": capability, "reason": "unsupported_capability"}

    def evidence_payload(self, search_result: dict = None) -> dict:
        sr = search_result or {}
        return {
            "selected_track": self.track,
            "connected": self.connected,
            "status": sr.get("status"),
            "objective": sr.get("objective"),
            "sources": [{"title": r.get("title"), "url": r.get("url")} for r in (sr.get("results") or [])],
        }

    def error_mapping(self, code: str) -> dict:
        mapping = {"401": "parallel_auth_failed", "429": "parallel_rate_limited", "5xx": "parallel_unavailable"}
        return {"code": code, "mapped": mapping.get(code, "parallel_error"), "retryable": code in ("429", "5xx")}


partner = PartnerAdapter()

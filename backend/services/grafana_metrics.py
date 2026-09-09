"""Grafana Cloud partner track — push LUMIÈRE agent metrics via Prometheus remote_write.

HARD REQUIREMENT: sending MUST fail silently. If Grafana Cloud is unreachable,
misconfigured, or anything raises, we log a warning and let the user flow continue.
Emitting a metric NEVER blocks a user operation (fire-and-forget async task).

Credentials come exclusively from environment variables (see backend/.env):
    GRAFANA_CLOUD_REMOTE_WRITE_URL   e.g. https://<region>.grafana.net/api/prom/push
    GRAFANA_CLOUD_INSTANCE_ID        numeric Metrics instance / user id (Basic Auth user)
    GRAFANA_CLOUD_API_TOKEN          Cloud Access Policy token with metrics:write scope

Metrics emitted (Prometheus classic types):
    lumiere_agent_duration_ms       histogram   label: agent
    lumiere_agent_calls_total       counter     labels: agent, status
    lumiere_agent_confidence        gauge       label: agent
    lumiere_story_completeness      gauge       label: experience_id
"""
from __future__ import annotations

import os
import time
import struct
import asyncio
import logging
import threading

log = logging.getLogger("lumiere.grafana")

URL = (os.environ.get("GRAFANA_CLOUD_REMOTE_WRITE_URL") or "").strip()
INSTANCE_ID = (os.environ.get("GRAFANA_CLOUD_INSTANCE_ID") or "").strip()
API_TOKEN = (os.environ.get("GRAFANA_CLOUD_API_TOKEN") or "").strip()

# Only these six agents are valid emission points per spec.
_AGENT_MAP = {
    "director": "director", "director agent": "director",
    "cinematographer": "cinematographer", "cinematographer agent": "cinematographer",
    "vision": "vision", "vision agent": "vision",
    "evaluator": "evaluator",
    "editor": "editor", "editor agent": "editor",
    "render worker": "render_worker", "render_worker": "render_worker",
}

# Duration histogram buckets (ms). Cover fast deterministic traces up to ~1min renders.
_BUCKETS = [50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000]

# In-process cumulative state (Prometheus counters/histograms must be monotonic).
_lock = threading.Lock()
_calls_total: dict = {}          # (agent, status) -> int
_hist: dict = {}                 # agent -> {"buckets": {le: int}, "count": int, "sum": float}


def _configured() -> bool:
    return bool(URL.startswith("https://") and INSTANCE_ID and API_TOKEN)


def _canon(agent: str):
    return _AGENT_MAP.get((agent or "").strip().lower())


# ----------------- minimal Prometheus remote_write protobuf encoder -----------------
def _varint(n: int) -> bytes:
    n = int(n)
    if n < 0:
        n &= (1 << 64) - 1
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _ld(field: int, data: bytes) -> bytes:            # length-delimited (wire type 2)
    return _tag(field, 2) + _varint(len(data)) + data


def _str(field: int, s: str) -> bytes:
    return _ld(field, s.encode("utf-8"))


def _double(field: int, v: float) -> bytes:           # wire type 1 (64-bit)
    return _tag(field, 1) + struct.pack("<d", float(v))


def _i64(field: int, v: int) -> bytes:                # wire type 0 (varint)
    return _tag(field, 0) + _varint(int(v))


def _label(name: str, value: str) -> bytes:
    return _str(1, name) + _str(2, value)


def _timeseries(labels: list, value: float, ts_ms: int) -> bytes:
    body = b"".join(_ld(1, _label(n, v)) for n, v in labels)
    body += _ld(2, _double(1, value) + _i64(2, ts_ms))
    return body


def _write_request(series: list) -> bytes:
    # series: list of (labels_list, value, ts_ms)
    return b"".join(_ld(1, _timeseries(lbls, val, ts)) for lbls, val, ts in series)
# ------------------------------------------------------------------------------------


def _labelset(metric: str, extra: dict) -> list:
    lbls = [("__name__", metric)]
    lbls += [(k, str(v)) for k, v in sorted(extra.items())]
    return lbls


def _build_agent_series(agent: str, status: str, latency_ms, confidence, ts_ms: int) -> list:
    series = []
    with _lock:
        if status is not None:
            key = (agent, str(status).lower())
            _calls_total[key] = _calls_total.get(key, 0) + 1
            series.append((_labelset("lumiere_agent_calls_total",
                                     {"agent": agent, "status": key[1]}), _calls_total[key], ts_ms))
        if latency_ms is not None:
            h = _hist.setdefault(agent, {"buckets": {b: 0 for b in _BUCKETS}, "count": 0, "sum": 0.0})
            h["count"] += 1
            h["sum"] += float(latency_ms)
            for b in _BUCKETS:
                if float(latency_ms) <= b:
                    h["buckets"][b] += 1
            for b in _BUCKETS:
                series.append((_labelset("lumiere_agent_duration_ms_bucket",
                                         {"agent": agent, "le": str(b)}), h["buckets"][b], ts_ms))
            series.append((_labelset("lumiere_agent_duration_ms_bucket",
                                     {"agent": agent, "le": "+Inf"}), h["count"], ts_ms))
            series.append((_labelset("lumiere_agent_duration_ms_count", {"agent": agent}), h["count"], ts_ms))
            series.append((_labelset("lumiere_agent_duration_ms_sum", {"agent": agent}), h["sum"], ts_ms))
    if confidence is not None:
        series.append((_labelset("lumiere_agent_confidence", {"agent": agent}), float(confidence), ts_ms))
    return series


async def _send(series: list) -> None:
    if not _configured() or not series:
        return
    try:
        import cramjam
        import httpx
        payload = _write_request(series)
        body = bytes(cramjam.snappy.compress_raw(payload))
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.5)) as client:
            resp = await client.post(
                URL, content=body, auth=(INSTANCE_ID, API_TOKEN),
                headers={"Content-Type": "application/x-protobuf",
                         "Content-Encoding": "snappy",
                         "X-Prometheus-Remote-Write-Version": "0.1.0",
                         "User-Agent": "lumiere/1.0"})
            resp.raise_for_status()
    except Exception as exc:  # never re-raise — metrics must not affect the user flow
        log.warning("Grafana Cloud metrics dropped: %s", type(exc).__name__)


def _fire(series: list) -> None:
    """Schedule the send without ever blocking or raising."""
    if not series:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send(series))
    except RuntimeError:
        # no running loop (sync context) — run in a throwaway thread, still fire-and-forget
        def _runner():
            try:
                asyncio.run(_send(series))
            except Exception as exc:
                log.warning("Grafana Cloud metrics dropped: %s", type(exc).__name__)
        threading.Thread(target=_runner, daemon=True).start()


def record_agent(agent: str, status=None, latency_ms=None, confidence=None) -> None:
    """Emit agent duration/calls/confidence. Only the six valid agents are sent."""
    try:
        if not _configured():
            return
        canon = _canon(agent)
        if not canon:
            return
        series = _build_agent_series(canon, status, latency_ms, confidence, int(time.time() * 1000))
        _fire(series)
    except Exception as exc:
        log.warning("Grafana Cloud metrics dropped: %s", type(exc).__name__)


def record_completeness(experience_id: str, score) -> None:
    """Emit the story completeness gauge (0-100) for an experience."""
    try:
        if not _configured() or score is None or not experience_id:
            return
        series = [(_labelset("lumiere_story_completeness", {"experience_id": str(experience_id)}),
                   float(score), int(time.time() * 1000))]
        _fire(series)
    except Exception as exc:
        log.warning("Grafana Cloud metrics dropped: %s", type(exc).__name__)

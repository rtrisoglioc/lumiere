"""fal.ai image generation via Emergent Universal Key (queue proxy).

Two selectable models: Recraft V3 (brand/vector/illustration, accepts palette)
and Ideogram v3. Returns PNG bytes. Blocking — call via asyncio.to_thread."""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
PROXY = os.environ.get("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com").rstrip("/")
CONTROL = f"{PROXY}/api/v1/fal"
QUEUE_ORIGIN = "https://queue.fal.run"

ENDPOINTS = {"recraft": "fal-ai/recraft/v3/text-to-image", "ideogram": "fal-ai/ideogram/v3"}


def _headers(extra=None):
    h = {"Authorization": f"Bearer {EMERGENT_LLM_KEY}", "Content-Type": "application/json"}
    if os.environ.get("job_id"):
        h["X-App-ID"] = h["X-Job-ID"] = os.environ["job_id"]
    if extra:
        h.update(extra)
    return h


def _hex_to_rgb(hx):
    hx = (hx or "").lstrip("#")
    if len(hx) != 6:
        return None
    return {"r": int(hx[0:2], 16), "g": int(hx[2:4], 16), "b": int(hx[4:6], 16)}


def _run(endpoint_id, payload, timeout=180):
    r = requests.post(f"{CONTROL}/proxy", headers=_headers({"X-Fal-Target-Url": f"{QUEUE_ORIGIN}/{endpoint_id}"}),
                      json=payload, timeout=60)
    r.raise_for_status()
    sub = r.json()
    status_url, response_url = sub["status_url"], sub["response_url"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = requests.get(status_url, headers=_headers(), timeout=30)
        s.raise_for_status()
        st = (s.json().get("status") or "").upper()
        if st in {"COMPLETED", "OK"}:
            res = requests.get(response_url, headers=_headers(), timeout=60)
            res.raise_for_status()
            return res.json()
        if st in {"FAILED", "CANCELLED", "CANCELED", "ERROR"}:
            raise RuntimeError(f"fal_failed: {st}")
        time.sleep(2)
    raise RuntimeError("fal_timeout")


def generate(model: str, prompt: str, palette: list = None) -> bytes:
    endpoint = ENDPOINTS.get(model)
    if not endpoint:
        raise ValueError("unknown_model")
    clean = f"{prompt} No text, no words, no letters, no typography, no captions."
    if model == "recraft":
        payload = {"prompt": clean, "image_size": "square_hd", "style": "digital_illustration"}
        colors = [c for c in (_hex_to_rgb(h) for h in (palette or [])) if c]
        if colors:
            payload["colors"] = colors
    else:  # ideogram
        payload = {"prompt": clean, "image_size": "square_hd", "rendering_speed": "BALANCED"}
    data = _run(endpoint, payload)
    images = data.get("images") or []
    if not images or not images[0].get("url"):
        raise RuntimeError("no_image")
    img = requests.get(images[0]["url"], timeout=60)
    img.raise_for_status()
    return img.content

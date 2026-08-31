"""Emergent Object Storage adapter (modular).

This is the media storage layer. It preserves originals non-destructively and
stores versioned derivatives (cuts) under separate paths. Swap this module to
migrate to Google Cloud Storage later without touching the domain logic.
"""
import os
import hashlib
from pathlib import Path
import requests

from db import WORKDIR

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "lumiere"

_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=180,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=180,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def delete_object(path: str) -> bool:
    key = init_storage()
    resp = requests.delete(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    return resp.status_code in (200, 202, 204, 404)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_path_for(experience_id: str, sub: str, filename: str) -> Path:
    d = WORKDIR / experience_id / sub
    d.mkdir(parents=True, exist_ok=True)
    return d / filename


def ensure_local(experience_id: str, sub: str, filename: str, storage_path: str) -> Path:
    """Return a local working copy, downloading from object storage if missing."""
    p = local_path_for(experience_id, sub, filename)
    if not p.exists() or p.stat().st_size == 0:
        data, _ = get_object(storage_path)
        p.write_bytes(data)
    return p

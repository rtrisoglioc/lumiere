"""B-roll insert library: AI-generated (Gemini via Universal Key) and stock
(Pexels) images the user can drop into a cut. Images stored in object storage."""
import os
import uuid
import base64
import asyncio

import requests
from fastapi import APIRouter, Depends, HTTPException, Response, Header, Query
from pydantic import BaseModel
from dotenv import load_dotenv

from db import db, now_iso
from auth import get_current_user
import storage

load_dotenv()
inserts_router = APIRouter(prefix="/api/inserts")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
IMAGE_MODEL = os.environ.get("SOCIAL_IMAGE_MODEL") or "gemini-3.1-flash-image-preview"
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")
EFFECTS = ["kenburns", "zoomout", "slide", "fade", "pulse"]


class AiIn(BaseModel):
    prompt: str


class StockSaveIn(BaseModel):
    url: str
    alt: str = ""


async def _store_insert(user_id, img_bytes, source, meta):
    iid = str(uuid.uuid4())
    path = f"{storage.APP_NAME}/inserts/{user_id}/{iid}.png"
    put = await asyncio.to_thread(storage.put_object, path, img_bytes, "image/png")
    doc = {"id": iid, "owner": user_id, "source": source, "storage_path": put["path"],
           "meta": meta, "created_at": now_iso()}
    await db.insert_assets.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@inserts_router.get("")
async def list_inserts(user: dict = Depends(get_current_user)):
    return await db.insert_assets.find({"owner": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@inserts_router.get("/config")
async def config(user: dict = Depends(get_current_user)):
    return {"stock_enabled": bool(PEXELS_KEY), "effects": EFFECTS}


@inserts_router.post("/ai")
async def ai_insert(body: AiIn, user: dict = Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"insert:{uuid.uuid4().hex[:8]}",
                   system_message="You generate premium cinematic B-roll still frames, photorealistic, film look.")
    chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
    _t, images = await chat.send_message_multimodal_response(
        UserMessage(text=f"Cinematic B-roll frame, 16:9, film grain, shallow depth of field. {body.prompt}"))
    if not images:
        raise HTTPException(status_code=502, detail="no_image")
    doc = await _store_insert(user["user_id"], base64.b64decode(images[0]["data"]), "ai", {"prompt": body.prompt})
    return doc


@inserts_router.get("/stock/search")
async def stock_search(q: str, user: dict = Depends(get_current_user)):
    if not PEXELS_KEY:
        raise HTTPException(status_code=503, detail="stock_not_configured")
    try:
        r = await asyncio.to_thread(lambda: requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": q, "per_page": 15, "orientation": "landscape"}, timeout=20))
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"pexels_failed: {e}")
    photos = r.json().get("photos", [])
    return [{"id": p["id"], "thumb": p["src"]["medium"], "full": p["src"]["large2x"],
             "alt": p.get("alt", ""), "photographer": p.get("photographer", "")} for p in photos]


@inserts_router.post("/stock/save")
async def stock_save(body: StockSaveIn, user: dict = Depends(get_current_user)):
    if not PEXELS_KEY:
        raise HTTPException(status_code=503, detail="stock_not_configured")
    try:
        r = await asyncio.to_thread(lambda: requests.get(body.url, timeout=30))
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"download_failed: {str(e)[:120]}")
    doc = await _store_insert(user["user_id"], r.content, "stock", {"alt": body.alt, "source_url": body.url})
    return doc


@inserts_router.get("/{insert_id}/image")
async def insert_image(insert_id: str, authorization: str = Header(default=None), auth: str = Query(default=None)):
    token = auth or (authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    doc = await db.insert_assets.find_one({"id": insert_id, "owner": session["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    data, ct = await asyncio.to_thread(storage.get_object, doc["storage_path"])
    return Response(content=data, media_type="image/png")


@inserts_router.delete("/{insert_id}")
async def delete_insert(insert_id: str, user: dict = Depends(get_current_user)):
    await db.insert_assets.delete_one({"id": insert_id, "owner": user["user_id"]})
    return {"ok": True}

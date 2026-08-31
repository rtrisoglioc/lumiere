"""AI Social Content Studio — Studio-plan exclusive (entitlement enforced).

Flow: brief/ideas -> LLM content plan + post drafts (copy, hashtags, network,
design prompt) -> per-post AI design image (Gemini Nano Banana) -> schedule
(network, date/time) -> simulated publish.

LLM & image generation run on the Emergent Universal Key (EMERGENT_LLM_KEY).
Publishing is SIMULATED for now (no real social network API calls)."""
import os
import re
import json
import uuid
import base64

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from dotenv import load_dotenv

from db import db, now_iso
from auth import get_current_user
import plans_store
import storage

load_dotenv()
social_router = APIRouter(prefix="/api/social")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
TEXT_MODEL = os.environ.get("SOCIAL_TEXT_MODEL") or "gemini-3.5-flash"
IMAGE_MODEL = os.environ.get("SOCIAL_IMAGE_MODEL") or "gemini-3.1-flash-image-preview"
NETWORKS = ["instagram", "facebook", "x", "linkedin", "tiktok"]


class PlanIn(BaseModel):
    brief: str
    count: int = 4


class PostUpdateIn(BaseModel):
    caption: dict = None
    hashtags: list = None
    network: str = None
    scheduled_at: str = None
    status: str = None


async def require_social(user: dict = Depends(get_current_user)) -> dict:
    plan = await plans_store.get_plan(user.get("plan") or "free")
    if not (plan.get("entitlements") or {}).get("social"):
        raise HTTPException(status_code=403, detail="social_not_entitled")
    return user


def _extract_json(text):
    if not isinstance(text, str):
        return text
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    cand = fence.group(1) if fence else text
    s, e = cand.find("{"), cand.rfind("}")
    if s != -1 and e != -1 and e > s:
        cand = cand[s:e + 1]
    try:
        return json.loads(cand)
    except Exception:
        return None


@social_router.post("/plan")
async def make_plan(body: PlanIn, user: dict = Depends(require_social)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    n = max(1, min(8, body.count))
    system = ("You are SOCIAL DIRECTOR, an agentic social media strategist for LUMIÈRE (a cinematic "
              "content studio). Return ONLY valid minified JSON. All human-facing text fields MUST be "
              'bilingual objects {"en":"...","es":"..."} with natural English AND Spanish.')
    prompt = (
        f"Creator ideas/brief: {body.brief!r}.\n"
        f"Produce a JSON object: {{\"plan\": {{\"summary\": bilingual, \"strategy\": bilingual}}, "
        f"\"posts\": array of exactly {n} objects {{\"title\": bilingual short, \"caption\": bilingual "
        "(1-3 sentences, engaging), \"hashtags\": array of 4-6 strings (no # inside), "
        f"\"network\": one of {NETWORKS}, \"design_prompt\": a concise English image-generation prompt "
        "for an on-brand cinematic social graphic, \"best_time\": bilingual suggested day/time}}}}."
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"social:{user['user_id']}:{uuid.uuid4().hex[:8]}",
                   system_message=system).with_model("gemini", TEXT_MODEL)
    raw = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(raw) or {}
    plan = data.get("plan") or {}
    posts_in = data.get("posts") or []
    created = []
    for p in posts_in[:n]:
        post = {
            "id": str(uuid.uuid4()),
            "owner": user["user_id"],
            "title": p.get("title"),
            "caption": p.get("caption"),
            "hashtags": p.get("hashtags") or [],
            "network": p.get("network") if p.get("network") in NETWORKS else "instagram",
            "design_prompt": p.get("design_prompt"),
            "best_time": p.get("best_time"),
            "image_path": None,
            "scheduled_at": None,
            "status": "draft",
            "created_at": now_iso(),
        }
        await db.social_posts.insert_one(dict(post))
        post.pop("_id", None)
        created.append(post)
    return {"plan": plan, "posts": created}


@social_router.get("/posts")
async def list_posts(user: dict = Depends(require_social)):
    return await db.social_posts.find({"owner": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


async def _get_post(post_id: str, user: dict) -> dict:
    post = await db.social_posts.find_one({"id": post_id, "owner": user["user_id"]}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@social_router.post("/posts/{post_id}/design")
async def generate_design(post_id: str, user: dict = Depends(require_social)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    post = await _get_post(post_id, user)
    prompt = (post.get("design_prompt") or "Cinematic on-brand social graphic, warm golden light, "
              "editorial, premium film aesthetic")
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"social-img:{post_id}",
                   system_message="You generate premium cinematic social media graphics.")
    chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
    _text, images = await chat.send_message_multimodal_response(
        UserMessage(text=f"Create a striking social media graphic (square). {prompt}"))
    if not images:
        raise HTTPException(status_code=502, detail="No image generated")
    img_bytes = base64.b64decode(images[0]["data"])
    path = f"{storage.APP_NAME}/social/{user['user_id']}/{post_id}.png"
    put = await __import__("asyncio").to_thread(storage.put_object, path, img_bytes, "image/png")
    await db.social_posts.update_one({"id": post_id}, {"$set": {"image_path": put["path"]}})
    return {"ok": True, "image_url": f"/api/social/posts/{post_id}/image"}


@social_router.get("/posts/{post_id}/image")
async def get_design(post_id: str, user: dict = Depends(require_social)):
    post = await _get_post(post_id, user)
    if not post.get("image_path"):
        raise HTTPException(status_code=404, detail="No image")
    data, ct = await __import__("asyncio").to_thread(storage.get_object, post["image_path"])
    return Response(content=data, media_type="image/png")


@social_router.put("/posts/{post_id}")
async def update_post(post_id: str, body: PostUpdateIn, user: dict = Depends(require_social)):
    await _get_post(post_id, user)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd.get("network") and upd["network"] not in NETWORKS:
        raise HTTPException(status_code=400, detail="invalid network")
    if upd:
        await db.social_posts.update_one({"id": post_id}, {"$set": upd})
    return await _get_post(post_id, user)


@social_router.post("/posts/{post_id}/schedule")
async def schedule_post(post_id: str, body: PostUpdateIn, user: dict = Depends(require_social)):
    await _get_post(post_id, user)
    if not body.scheduled_at or not body.network:
        raise HTTPException(status_code=400, detail="network and scheduled_at required")
    await db.social_posts.update_one(
        {"id": post_id},
        {"$set": {"network": body.network, "scheduled_at": body.scheduled_at, "status": "scheduled"}})
    return await _get_post(post_id, user)


@social_router.post("/posts/{post_id}/publish")
async def publish_post(post_id: str, user: dict = Depends(require_social)):
    """SIMULATED publish — flips status to 'published'. No real network API call yet."""
    await _get_post(post_id, user)
    await db.social_posts.update_one(
        {"id": post_id}, {"$set": {"status": "published", "published_at": now_iso(), "simulated": True}})
    return await _get_post(post_id, user)


@social_router.delete("/posts/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(require_social)):
    await _get_post(post_id, user)
    await db.social_posts.delete_one({"id": post_id, "owner": user["user_id"]})
    return {"ok": True}

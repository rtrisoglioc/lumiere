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
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv

from db import db, now_iso
from auth import get_current_user
import plans_store
import storage
import image_overlay

logger = logging.getLogger("lumiere")

load_dotenv()
social_router = APIRouter(prefix="/api/social")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
TEXT_MODEL = os.environ.get("SOCIAL_TEXT_MODEL") or "gemini-3.5-flash"
IMAGE_MODEL = os.environ.get("SOCIAL_IMAGE_MODEL") or "gemini-3.1-flash-image-preview"
NETWORKS = ["instagram", "facebook", "x", "linkedin", "tiktok"]


class PlanIn(BaseModel):
    brief: str
    count: int = 4
    tone: str = None


class BrandIn(BaseModel):
    name: str = None
    colors: list = None
    auto_logo: bool = None
    image_style: str = None
    website: str = None


STYLE_PRESETS = {
    "infographic": ("Modern flat EDUCATIONAL INFOGRAPHIC social graphic. Soft pastel brand-colored background "
                    "with subtle abstract wave/blob shapes, a friendly stylized 3D-rendered (clay/Blender look) "
                    "character or clean vector illustration as the focal element, a bold title area, and a tidy "
                    "vertical checklist / bullet list with check icons. Generous negative space, balanced layout, "
                    "premium corporate look, crisp and uncluttered. STRICTLY NO photorealistic photographs of real people."),
    "illustration3d": ("Playful 3D-rendered illustration (clay/Blender style) of stylized rounded characters and "
                       "objects on a clean brand-colored background, soft studio lighting, modern corporate marketing "
                       "aesthetic, plenty of clean space. NO photorealistic humans, NO real photos."),
    "flatvector": ("Minimal FLAT VECTOR illustration with geometric shapes, limited brand palette, clean lines and "
                   "simple line-icons, corporate presentation aesthetic, lots of whitespace. NO photos, NO realistic people."),
    "minimal": ("Ultra-minimal corporate graphic: solid brand-color background, one simple abstract shape or line-icon, "
                "large clean area reserved for a title. NO photos of people."),
    "poster": ("BOLD social POSTER / trend style: a solid vivid single-color background in the brand color, HUGE "
               "impactful display typography headline (2-3 words, stacked, all caps), ONE playful stylized 3D-rendered "
               "mascot/character (clay/Blender look) centered, the brand logo/name at the TOP and a short catchy handle "
               "or tagline at the BOTTOM. High energy, punchy, meme-ready. STRICTLY NO photorealistic real people."),
    "badge": ("Premium EMBLEM / BADGE / seal design (certification style): a centered circular badge with a ribbon or "
              "medal accent, a bold title above it, and the brand name inside a rounded pill at the bottom, on a "
              "smooth brand-colored gradient background with subtle large watermark text behind. Corporate, trustworthy, "
              "high-end. NO photos of people."),
    "photo": ("Premium cinematic photograph, editorial magazine quality, tasteful depth of field, professional lighting."),
}
STYLE_LABELS = list(STYLE_PRESETS.keys())


def _brand_directives(brand: dict) -> str:
    bits = []
    if brand.get("name"):
        bits.append(f"Brand name: {brand['name']}.")
    cols = [c for c in (brand.get("colors") or []) if c]
    if cols:
        bits.append(f"Use this exact brand color palette: {', '.join(cols)}.")
    return " ".join(bits)


def _style_directive(brand: dict) -> str:
    return STYLE_PRESETS.get(brand.get("image_style") or "infographic", STYLE_PRESETS["infographic"])


async def _get_brand(user_id: str) -> dict:
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return ((u or {}).get("preferences") or {}).get("brand") or {}


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


@social_router.get("/brand")
async def get_brand(user: dict = Depends(require_social)):
    brand = await _get_brand(user["user_id"])
    u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"brand": brand, "has_logo": ((u or {}).get("preferences") or {}).get("has_logo", False),
            "styles": STYLE_LABELS}


@social_router.put("/brand")
async def put_brand(body: BrandIn, user: dict = Depends(require_social)):
    upd = {f"preferences.brand.{k}": v for k, v in body.model_dump().items() if v is not None}
    if upd:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": upd})
    return await get_brand(user)


@social_router.post("/plan")
async def make_plan(body: PlanIn, user: dict = Depends(require_social)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    n = max(1, min(8, body.count))
    brand = await _get_brand(user["user_id"])
    brand_line = _brand_directives(brand)
    style_line = _style_directive(brand)
    tone = (body.tone or "warm, cinematic, confident").strip()
    system = ("You are SOCIAL DIRECTOR, an elite agentic social media strategist and copywriter for LUMIÈRE "
              "(a cinematic content studio). Return ONLY valid minified JSON. All human-facing text fields MUST be "
              'bilingual objects {"en":"...","es":"..."} with natural, native-level English AND Spanish. '
              "Captions must be EXTENSIVE and engaging: a scroll-stopping hook line, then 2-4 short paragraphs of "
              "story/value separated by \\n\\n line breaks, then a clear call-to-action, and 1-3 tasteful emojis "
              "used sparingly. Aim for 150-230 words per caption.")
    prompt = (
        f"Creator ideas/brief: {body.brief!r}. Desired tone: {tone}.\n"
        f"Brand context for the visuals: {brand_line}\n"
        f"Visual style REQUIRED for every design_prompt: {style_line}\n"
        f"Produce a JSON object: {{\"plan\": {{\"summary\": bilingual, \"strategy\": bilingual}}, "
        f"\"posts\": array of exactly {n} objects {{\"title\": bilingual short, \"caption\": bilingual "
        "EXTENSIVE (150-230 words, hook + \\n\\n paragraphs + CTA, sparing emojis), "
        "\"hashtags\": array of 6-10 relevant strings (no # inside), "
        f"\"network\": one of {NETWORKS}, \"design_prompt\": a rich, detailed English image-generation prompt "
        "that FOLLOWS the required visual style above (describe the illustrated subject, layout, title area and "
        "bullet/checklist content, and the brand palette) — do NOT describe photographs of real people, "
        "\"best_time\": bilingual suggested day/time}}}}."
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
    import asyncio
    post = await _get_post(post_id, user)
    brand = await _get_brand(user["user_id"])
    base_prompt = (post.get("design_prompt") or "Educational post about the brand's core value")
    prompt = f"{_style_directive(brand)}\nTOPIC/SUBJECT: {base_prompt}.\n{_brand_directives(brand)}"
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"social-img:{post_id}:{uuid.uuid4().hex[:6]}",
                   system_message=("You generate premium BRANDED MARKETING GRAPHICS (flat/3D illustrations and "
                                   "infographics). Never output photorealistic photographs of real people unless the "
                                   "style explicitly says 'photo'. Keep composition clean with space for text."))
    chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
    _text, images = await chat.send_message_multimodal_response(
        UserMessage(text=f"Create a striking, professional social media graphic (square, 1:1). {prompt}"))
    if not images:
        raise HTTPException(status_code=502, detail="No image generated")
    img_bytes = base64.b64decode(images[0]["data"])
    path = f"{storage.APP_NAME}/social/{user['user_id']}/{post_id}.png"
    put = await asyncio.to_thread(storage.put_object, path, img_bytes, "image/png")
    set_fields = {"image_path": put["path"]}
    unset_fields = {"overlay_path": ""}

    # Auto-brand: stamp the logo (corner) and website (footer) if enabled in the Brand Kit.
    website = (brand.get("website") or "").strip()
    if brand.get("auto_logo") or website:
        u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        lp = ((u or {}).get("preferences") or {}).get("logo_path")
        logo_bytes, logo_opts, text_opts = None, {}, {}
        if brand.get("auto_logo") and lp:
            logo_bytes = (await asyncio.to_thread(storage.get_object, lp))[0]
            logo_opts = {"enabled": True, "x": 0.96, "y": 0.05, "scale": 0.16, "opacity": 0.98}
        if website:
            color = (brand.get("colors") or ["#111111"])[0]
            text_opts = {"enabled": True, "content": website, "position": "bottom", "color": color, "size": 0.035}
        if logo_bytes or text_opts:
            try:
                out = await asyncio.to_thread(image_overlay.apply_overlay, img_bytes, logo_bytes, logo_opts, text_opts)
                opath = f"{storage.APP_NAME}/social/{user['user_id']}/{post_id}_overlay.png"
                oput = await asyncio.to_thread(storage.put_object, opath, out, "image/png")
                set_fields["overlay_path"] = oput["path"]
                set_fields["overlay_opts"] = {"logo": logo_opts, "text": text_opts}
                unset_fields = {}
            except Exception as e:
                logger.warning(f"auto-brand overlay failed: {e}")

    op = {"$set": set_fields}
    if unset_fields:
        op["$unset"] = unset_fields
    await db.social_posts.update_one({"id": post_id}, op)
    return {"ok": True, "image_url": f"/api/social/posts/{post_id}/image"}


@social_router.get("/posts/{post_id}/image")
async def get_design(post_id: str, user: dict = Depends(require_social)):
    post = await _get_post(post_id, user)
    path = post.get("overlay_path") or post.get("image_path")
    if not path:
        raise HTTPException(status_code=404, detail="No image")
    data, ct = await __import__("asyncio").to_thread(storage.get_object, path)
    return Response(content=data, media_type="image/png")


class OverlayIn(BaseModel):
    logo: dict = None
    text: dict = None
    texts: list = None


@social_router.post("/posts/{post_id}/upload-image")
async def upload_own_image(post_id: str, file: UploadFile = File(...), user: dict = Depends(require_social)):
    """Use a real uploaded photo as the post image (instead of AI generation)."""
    post = await _get_post(post_id, user)
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file_too_large")
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        import io as _io
        img = Image.open(_io.BytesIO(data)).convert("RGB")
        buf = _io.BytesIO(); img.save(buf, format="PNG"); png = buf.getvalue()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_image")
    path = f"{storage.APP_NAME}/social/{user['user_id']}/{post_id}_upload.png"
    put = await __import__("asyncio").to_thread(storage.put_object, path, png, "image/png")
    await db.social_posts.update_one({"id": post_id}, {"$set": {"image_path": put["path"]}, "$unset": {"overlay_path": ""}})
    return {"ok": True, "image_url": f"/api/social/posts/{post_id}/image"}


@social_router.post("/posts/{post_id}/overlay")
async def overlay_design(post_id: str, body: OverlayIn, user: dict = Depends(require_social)):
    """Composite the user logo and/or a text headline onto the post image
    (non-destructive: always rebuilt from the original AI image)."""
    import asyncio
    post = await _get_post(post_id, user)
    if not post.get("image_path"):
        raise HTTPException(status_code=400, detail="no_base_image")
    logo = body.logo or {}
    texts = body.texts if body.texts is not None else ([body.text] if body.text else [])
    texts = [t for t in texts if t and (t.get("content") or "").strip()]
    if not (logo.get("enabled") or texts):
        # clear overlay -> revert to original
        await db.social_posts.update_one({"id": post_id}, {"$unset": {"overlay_path": ""}})
        return {"ok": True, "cleared": True, "image_url": f"/api/social/posts/{post_id}/image"}

    base_bytes = (await asyncio.to_thread(storage.get_object, post["image_path"]))[0]
    logo_bytes = None
    if logo.get("enabled"):
        u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        lp = (u.get("preferences") or {}).get("logo_path")
        if lp:
            logo_bytes = (await asyncio.to_thread(storage.get_object, lp))[0]
        else:
            logo["enabled"] = False
    out = await asyncio.to_thread(image_overlay.apply_overlay, base_bytes, logo_bytes, logo, None, texts)
    path = f"{storage.APP_NAME}/social/{user['user_id']}/{post_id}_overlay.png"
    put = await asyncio.to_thread(storage.put_object, path, out, "image/png")
    await db.social_posts.update_one({"id": post_id}, {"$set": {"overlay_path": put["path"], "overlay_opts": {"logo": logo, "texts": texts}}})
    return {"ok": True, "image_url": f"/api/social/posts/{post_id}/image"}


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

import os
import uuid
import asyncio
import logging
import tempfile
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Header, Query, BackgroundTasks, Request
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from db import db, now_iso, WORKDIR
import storage
import ffmpeg_worker as ff
import inserts
from agent_adapter import agent_builder
from partner_adapter import partner
from vertex_video_adapter import vertex_video
import plans as plan_catalog
import plans_store
import music as music_lib
import agents
import orchestrator
import video_editor
import captions
from auth import exchange_session, get_current_user, logout as do_logout
from admin import admin_router
from payments import payments_router
from inserts_router import inserts_router
from v2 import v2_router, public_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("lumiere")

app = FastAPI(title="LUMIERE API")
api = APIRouter(prefix="/api")

MIME = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "m4v": "video/x-m4v",
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "heic": "image/heic"}


# ---------- models ----------
class SessionIn(BaseModel):
    session_id: str

class ExperienceIn(BaseModel):
    title: str
    type: str = "travel"
    language: str = "en"
    location_name: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    target_platform: str = "cinematic"

class PlanIn(BaseModel):
    intent: str

class ReviseIn(BaseModel):
    instruction: str
    music_id: Optional[str] = None

class CutIn(BaseModel):
    music_id: Optional[str] = None

class PlanIn2(BaseModel):
    plan: str

class VideoGenIn(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    duration_sec: int = 6
    style: str = "cinematic"

class VideoEnhanceIn(BaseModel):
    asset_id: str
    mode: str = "enhance"


# ---------- helpers ----------
async def get_experience(exp_id: str, user: dict) -> dict:
    exp = await db.experiences.find_one({"id": exp_id, "owner": user["user_id"]}, {"_id": 0})
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
    return exp


def ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"


async def usable_segments_for(exp_id: str):
    assets = await db.media_assets.find({"experience_id": exp_id, "status": "analyzed"}, {"_id": 0}).to_list(200)
    out = []
    for a in assets:
        analysis = a.get("analysis") or {}
        for i, seg in enumerate(analysis.get("segments") or []):
            if seg.get("usable", True):
                out.append({
                    "asset_id": a["id"],
                    "segment_index": i,
                    "segment_start_sec": seg.get("start_sec", 0),
                    "segment_end_sec": seg.get("end_sec", 3),
                    "quality": seg.get("quality", 0.6),
                    "label": seg.get("label"),
                    "mission_id": a.get("mission_id"),
                })
    return out


async def analyzed_summary(exp_id: str):
    assets = await db.media_assets.find({"experience_id": exp_id, "status": "analyzed"}, {"_id": 0}).to_list(200)
    summ = {}
    for a in assets:
        an = a.get("analysis") or {}
        summ[a["id"]] = {
            "scene": an.get("scene"),
            "usable": (an.get("technical") or {}).get("usable"),
            "narrative_relevance": an.get("narrative_relevance"),
            "segments": [{"start_sec": s.get("start_sec"), "end_sec": s.get("end_sec"),
                          "usable": s.get("usable"), "quality": s.get("quality")}
                         for s in (an.get("segments") or [])],
            "mission_id": a.get("mission_id"),
        }
    return summ


# ---------- background tasks ----------
async def analyze_asset_task(exp_id: str, asset_id: str):
    asset = await db.media_assets.find_one({"id": asset_id}, {"_id": 0})
    exp = await db.experiences.find_one({"id": exp_id}, {"_id": 0})
    if not asset or not exp:
        return
    try:
        local = await asyncio.to_thread(storage.ensure_local, exp_id, "originals",
                                        asset["local_name"], asset["storage_path"])
        info = await asyncio.to_thread(ff.probe, str(local))
        mission = None
        for m in (exp.get("missions") or {}).get("missions", []) if isinstance(exp.get("missions"), dict) else []:
            if m.get("id") == asset.get("mission_id"):
                mission = m
        file_ref = {"asset_id": asset_id, "path": str(local), "mime": asset["content_type"]}
        analysis, meta = await agents.vision_analyze(exp, exp.get("plan") or {}, mission, file_ref)
        await db.media_assets.update_one(
            {"id": asset_id},
            {"$set": {"status": "analyzed", "analysis": analysis, "probe": info,
                      "analysis_latency_ms": meta.get("latency_ms"), "analyzed_at": now_iso()}},
        )
    except Exception as e:
        logger.exception("analysis failed")
        await db.media_assets.update_one({"id": asset_id}, {"$set": {"status": "failed", "error": str(e)[:300]}})


async def render_cut_task(exp_id: str, cut_id: str):
    cut = await db.cut_versions.find_one({"id": cut_id}, {"_id": 0})
    if not cut:
        return
    try:
        edl = cut.get("edl") or []
        asset_ids = {c["asset_id"] for c in edl}
        resolved = {}
        for aid in asset_ids:
            a = await db.media_assets.find_one({"id": aid}, {"_id": 0})
            if not a:
                continue
            local = await asyncio.to_thread(storage.ensure_local, exp_id, "originals", a["local_name"], a["storage_path"])
            has_audio = (a.get("probe") or {}).get("has_audio", False)
            resolved[aid] = (str(local), has_audio)

        def resolver(aid):
            return resolved.get(aid)

        tmp = WORKDIR / exp_id / "tmp" / cut_id
        out = WORKDIR / exp_id / "cuts" / f"{cut_id}.mp4"
        result = await asyncio.to_thread(ff.render_cut, edl, resolver, tmp, out)
        if not result.get("ok"):
            await db.cut_versions.update_one({"id": cut_id}, {"$set": {"status": "failed", "error": result.get("error")}})
            return

        final = out
        music_id = cut.get("music_id")
        if music_id:
            track = await music_lib.get_track(music_id)
            if track:
                mpath = await asyncio.to_thread(storage.ensure_local, exp_id, "music",
                                                f"{music_id}.mp3", track["storage_path"])
                scored = WORKDIR / exp_id / "cuts" / f"{cut_id}_scored.mp4"
                ok = await asyncio.to_thread(ff.add_music, out, mpath, scored)
                if ok:
                    final = scored

        data = final.read_bytes()
        storage_path = f"{storage.APP_NAME}/derivatives/{exp_id}/{cut_id}.mp4"
        put = await asyncio.to_thread(storage.put_object, storage_path, data, "video/mp4")
        await db.cut_versions.update_one(
            {"id": cut_id},
            {"$set": {"status": "ready", "storage_path": put["path"], "duration_sec": result.get("duration"),
                      "clip_count": result.get("clips"), "size": put.get("size"), "rendered_at": now_iso()}},
        )
    except Exception as e:
        logger.exception("render failed")
        await db.cut_versions.update_one({"id": cut_id}, {"$set": {"status": "failed", "error": str(e)[:300]}})


# ---------- auth ----------
@api.post("/auth/session")
async def auth_session(body: SessionIn, response: Response):
    result = await exchange_session(body.session_id)
    response.set_cookie("session_token", result["session_token"], httponly=True, secure=True,
                        samesite="none", path="/", max_age=3600)
    return {"user": result["user"], "session_token": result["session_token"]}

@api.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return user

@api.post("/auth/logout")
async def auth_logout(response: Response, session_token: str = Header(default=None, alias="X-Session-Token"),
                      cookie_token: str = Query(default=None)):
    token = session_token or cookie_token
    if token:
        await do_logout(token)
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ---------- health / adapters ----------
@api.get("/agent/health")
async def agent_health():
    return agent_builder.status()

@api.get("/partner/health")
async def partner_health():
    return partner.health_check()


# ---------- experiences ----------
@api.post("/experiences")
async def create_experience(body: ExperienceIn, user: dict = Depends(get_current_user)):
    import geocode
    lat, lng = body.location_lat, body.location_lng
    if body.location_name and (lat is None or lng is None):
        lat, lng = await asyncio.to_thread(geocode.geocode, body.location_name)
    exp = {
        "id": str(uuid.uuid4()),
        "owner": user["user_id"],
        "title": body.title,
        "type": body.type,
        "language": body.language,
        "visibility": "private",
        "privacy": "private",
        "phase": "before",
        "location_name": body.location_name,
        "location_lat": lat,
        "location_lng": lng,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "target_platform": body.target_platform,
        "stage": "intent",
        "status": "DRAFT",
        "intent": None,
        "plan": None,
        "missions": None,
        "completeness": None,
        "created_at": now_iso(),
    }
    # Soft counter (Free = 1 experience). Informative only — NEVER blocks creation.
    prior = 0
    try:
        prior = await db.experiences.count_documents({"owner": user["user_id"], "status": {"$ne": "trashed"}})
    except Exception:
        prior = 0
    await db.experiences.insert_one(dict(exp))
    exp.pop("_id", None)
    exp["soft_limit_notice"] = prior >= 1
    return exp

@api.get("/experiences")
async def list_experiences(user: dict = Depends(get_current_user)):
    return await db.experiences.find(
        {"owner": user["user_id"], "status": {"$ne": "trashed"}}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)

@api.get("/experiences/{exp_id}")
async def get_experience_full(exp_id: str, user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    exp["media"] = await db.media_assets.find({"experience_id": exp_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    exp["cuts"] = await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0}).sort("version", 1).to_list(100)
    return exp


# ---------- planning ----------
@api.post("/experiences/{exp_id}/plan")
async def make_plan(exp_id: str, body: PlanIn, user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    correlation_id = str(uuid.uuid4())
    context, cmeta = await agents.context_agent(exp, body.intent, correlation_id)
    plan, pmeta = await agents.director_plan(exp, body.intent, context, correlation_id)
    exp["plan"] = plan
    missions, mmeta = await agents.cinematographer_missions(exp, plan, context, correlation_id)
    await db.experiences.update_one(
        {"id": exp_id},
        {"$set": {"intent": body.intent, "context": context, "plan": plan, "missions": missions,
                  "stage": "capture", "correlation_id": correlation_id}},
    )
    return {"plan": plan, "missions": missions, "context": context, "correlation_id": correlation_id,
            "partner_connected": bool(context.get("ok")),
            "latency_ms": (pmeta.get("latency_ms", 0) + mmeta.get("latency_ms", 0))}


# ---------- media ----------
@api.post("/experiences/{exp_id}/upload")
async def upload_media(exp_id: str, background: BackgroundTasks, file: UploadFile = File(...),
                       mission_id: str = Form(default=None), user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    ext = ext_of(file.filename)
    data = await file.read()
    checksum = storage.sha256_hex(data)
    asset_id = str(uuid.uuid4())
    local_name = f"{asset_id}.{ext}"
    content_type = file.content_type or MIME.get(ext, "application/octet-stream")
    storage_path = f"{storage.APP_NAME}/originals/{exp_id}/{local_name}"

    put = await asyncio.to_thread(storage.put_object, storage_path, data, content_type)

    asset = {
        "id": asset_id,
        "experience_id": exp_id,
        "owner": user["user_id"],
        "mission_id": mission_id,
        "original_filename": file.filename,
        "local_name": local_name,
        "storage_path": put["path"],
        "content_type": content_type,
        "kind": "image" if content_type.startswith("image") else "video",
        "size": put.get("size", len(data)),
        "checksum_sha256": checksum,
        "status": "processing",
        "analysis": None,
        "created_at": now_iso(),
    }
    await db.media_assets.insert_one(dict(asset))
    asset.pop("_id", None)
    background.add_task(analyze_asset_task, exp_id, asset_id)
    return asset

@api.get("/experiences/{exp_id}/media")
async def list_media(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    return await db.media_assets.find({"experience_id": exp_id}, {"_id": 0}).sort("created_at", 1).to_list(200)

@api.get("/media/{asset_id}")
async def get_media(asset_id: str, user: dict = Depends(get_current_user)):
    a = await db.media_assets.find_one({"id": asset_id, "owner": user["user_id"]}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    return a


# ---------- evaluate / completeness ----------
@api.post("/experiences/{exp_id}/evaluate")
async def evaluate(exp_id: str, user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    if not exp.get("plan"):
        raise HTTPException(status_code=400, detail="No plan yet")
    summ = await analyzed_summary(exp_id)
    if not summ:
        raise HTTPException(status_code=400, detail="No analyzed footage yet")
    missions = (exp.get("missions") or {}).get("missions", [])
    result, meta = await agents.evaluator_assess(exp, exp["plan"], missions, summ)
    await db.experiences.update_one({"id": exp_id}, {"$set": {"completeness": result, "stage": "editing"}})
    return {"completeness": result, "latency_ms": meta.get("latency_ms")}


# ---------- cuts ----------
async def _next_version(exp_id: str) -> int:
    last = await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0, "version": 1}).sort("version", -1).to_list(1)
    return (last[0]["version"] + 1) if last else 1

@api.post("/experiences/{exp_id}/cut")
async def make_cut(exp_id: str, background: BackgroundTasks, body: CutIn = CutIn(), user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    if not exp.get("plan"):
        raise HTTPException(status_code=400, detail="No plan yet")
    segs = await usable_segments_for(exp_id)
    if not segs:
        raise HTTPException(status_code=400, detail="No usable segments yet")
    edl_out, meta = await agents.editor_edl(exp, exp["plan"], segs)
    edl = edl_out.get("edl", []) if isinstance(edl_out, dict) else []
    valid_assets = {s["asset_id"] for s in segs}
    edl = [c for c in edl if c.get("asset_id") in valid_assets]
    if not edl:
        edl = [{"asset_id": s["asset_id"], "segment_start_sec": s["segment_start_sec"],
                "segment_end_sec": s["segment_end_sec"], "order": i, "transition": "cut"}
               for i, s in enumerate(segs)]
    version = await _next_version(exp_id)
    cut = {
        "id": str(uuid.uuid4()),
        "experience_id": exp_id,
        "owner": user["user_id"],
        "version": version,
        "parent_id": None,
        "kind": "initial",
        "instruction": None,
        "edl": edl,
        "music_id": body.music_id,
        "editor_meta": {k: edl_out.get(k) for k in ("rationale", "target_duration_sec", "confidence")} if isinstance(edl_out, dict) else {},
        "status": "rendering",
        "storage_path": None,
        "created_at": now_iso(),
    }
    await db.cut_versions.insert_one(dict(cut))
    cut.pop("_id", None)
    background.add_task(render_cut_task, exp_id, cut["id"])
    return cut

@api.get("/experiences/{exp_id}/cuts")
async def list_cuts(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    return await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0}).sort("version", 1).to_list(100)

@api.get("/cuts/{cut_id}")
async def get_cut(cut_id: str, user: dict = Depends(get_current_user)):
    c = await db.cut_versions.find_one({"id": cut_id, "owner": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return c

@api.post("/cuts/{cut_id}/revise")
async def revise_cut(cut_id: str, body: ReviseIn, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    parent = await db.cut_versions.find_one({"id": cut_id, "owner": user["user_id"]}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Cut not found")
    exp = await db.experiences.find_one({"id": parent["experience_id"]}, {"_id": 0})
    segs = await usable_segments_for(exp["id"])
    out, meta = await agents.reviser_revise(exp, exp.get("plan") or {}, parent["edl"], segs, body.instruction)
    edl = out.get("edl", []) if isinstance(out, dict) else []
    valid_assets = {s["asset_id"] for s in segs}
    edl = [c for c in edl if c.get("asset_id") in valid_assets] or parent["edl"]
    version = await _next_version(exp["id"])
    cut = {
        "id": str(uuid.uuid4()),
        "experience_id": exp["id"],
        "owner": user["user_id"],
        "version": version,
        "parent_id": parent["id"],
        "kind": "revision",
        "instruction": body.instruction,
        "edl": edl,
        "music_id": body.music_id or parent.get("music_id"),
        "edit_decisions": out.get("edit_decisions") if isinstance(out, dict) else [],
        "requires_confirmation": out.get("requires_confirmation", False) if isinstance(out, dict) else False,
        "reviser_summary": out.get("summary") if isinstance(out, dict) else None,
        "status": "rendering",
        "storage_path": None,
        "created_at": now_iso(),
    }
    await db.cut_versions.insert_one(dict(cut))
    cut.pop("_id", None)
    background.add_task(render_cut_task, exp["id"], cut["id"])
    return cut


class RemoveClipIn(BaseModel):
    asset_id: str


class ProEditIn(BaseModel):
    aspect: str = "16:9"
    filter: str = "none"
    speed: float = 1.0
    transition: str = "none"
    music_id: Optional[str] = None
    logo: Optional[dict] = None
    captions: Optional[dict] = None
    inserts: Optional[list] = None
    text_overlay: Optional[dict] = None
    transition_speed: Optional[str] = None
    music_volume: Optional[float] = None


@api.post("/cuts/{cut_id}/pro-edit")
async def pro_edit_cut(cut_id: str, body: ProEditIn, user: dict = Depends(get_current_user)):
    """Pro editor for an Experience CUT: format 16:9/9:16/1:1, color look, speed,
    transition stock and music — applied via FFmpeg into a new CutVersion."""
    parent = await db.cut_versions.find_one({"id": cut_id, "owner": user["user_id"]}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Cut not found")
    if parent.get("status") != "ready" or not parent.get("storage_path"):
        raise HTTPException(status_code=400, detail="cut_not_ready")
    exp_id = parent["experience_id"]
    edl = parent.get("edl") or []
    TDUR = {"slow": 1.0, "med": 0.5, "fast": 0.25}.get(body.transition_speed or "med", 0.5)
    scene_transition = body.transition in ff.XFADE_MAP and len(edl) >= 2
    effective_transition = body.transition
    base_tmp = None
    if scene_transition:
        # Re-render from the ORIGINAL segments with real between-scene transitions.
        resolved = {}
        for aid in {c["asset_id"] for c in edl}:
            a = await db.media_assets.find_one({"id": aid}, {"_id": 0})
            if not a:
                continue
            try:
                local = await asyncio.to_thread(storage.ensure_local, exp_id, "originals", a["local_name"], a["storage_path"])
            except Exception:
                continue
            resolved[aid] = (str(local), (a.get("probe") or {}).get("has_audio", False))

        if len(resolved) >= 2 or (resolved and len(edl) >= 2):
            base_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
            trdir = WORKDIR / exp_id / "tmp" / f"protrans_{uuid.uuid4().hex[:8]}"
            res = await asyncio.to_thread(ff.render_cut_with_transitions, edl,
                                          lambda aid: resolved.get(aid), trdir, Path(base_tmp), body.transition, TDUR)
            if res.get("ok"):
                src_bytes = Path(base_tmp).read_bytes()
                effective_transition = "none"  # transitions already baked between scenes
            else:
                logger.warning(f"scene transitions failed: {res.get('error')}")
                src_bytes = (await asyncio.to_thread(storage.get_object, parent["storage_path"]))[0]
        else:
            src_bytes = (await asyncio.to_thread(storage.get_object, parent["storage_path"]))[0]
    else:
        src_bytes = (await asyncio.to_thread(storage.get_object, parent["storage_path"]))[0]

    music_tmp = logo_tmp = None
    if body.music_id:
        track = await music_lib.get_track(body.music_id)
        if track and track.get("storage_path"):
            mb = (await asyncio.to_thread(storage.get_object, track["storage_path"]))[0]
            music_tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            Path(music_tmp).write_bytes(mb)
    logo = body.logo or {}
    if logo.get("enabled"):
        u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        lp = (u.get("preferences") or {}).get("logo_path")
        if lp:
            lb = (await asyncio.to_thread(storage.get_object, lp))[0]
            logo_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            Path(logo_tmp).write_bytes(lb)
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"preferences.logo": logo}})

    src_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    Path(src_tmp).write_bytes(src_bytes)
    edit_src = src_tmp
    insert_tmp = None

    # B-roll inserts (stock/AI) spliced into the base by timestamp.
    insert_specs = []
    for it in (body.inserts or []):
        a = await db.insert_assets.find_one({"id": it.get("id"), "owner": user["user_id"]}, {"_id": 0})
        if not a:
            continue
        ib = (await asyncio.to_thread(storage.get_object, a["storage_path"]))[0]
        ip = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        Path(ip).write_bytes(ib)
        insert_specs.append({"image_path": ip, "at_sec": it.get("at_sec", 0),
                             "duration": it.get("duration", 2.0), "effect": it.get("effect", "kenburns")})
    if insert_specs:
        insert_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
        idir = WORKDIR / exp_id / "tmp" / f"inserts_{uuid.uuid4().hex[:8]}"
        join = effective_transition if effective_transition in ff.XFADE_MAP else "fade"
        res_i = await asyncio.to_thread(inserts.splice_inserts, src_tmp, insert_specs, Path(insert_tmp), idir, join)
        for s in insert_specs:
            try:
                Path(s["image_path"]).unlink(missing_ok=True)
            except Exception:
                pass
        if res_i.get("ok"):
            edit_src = insert_tmp
        else:
            logger.warning(f"inserts failed: {res_i.get('error')}")

    caps = body.captions or {}
    sub_tmp = None
    captions_status = "off"
    if caps.get("enabled"):
        W, H = video_editor.ASPECT_DIMS.get(body.aspect, video_editor.ASPECT_DIMS["16:9"])
        try:
            sub_tmp = await captions.generate_ass(edit_src, W, H, float(body.speed or 1),
                                                  caps.get("style", "bold"), caps.get("lang") or None)
        except Exception as e:
            logger.warning(f"captions failed (cut): {e}")
        captions_status = "applied" if sub_tmp else "no_speech"
    opts = {"aspect": body.aspect, "filter": body.filter, "speed": body.speed,
            "transition": effective_transition, "logo": logo,
            "text_overlay": body.text_overlay, "transition_dur": TDUR,
            "music_volume": body.music_volume if body.music_volume is not None else 0.85}
    try:
        await asyncio.to_thread(video_editor.transform_video, edit_src, out_tmp, opts, logo_tmp, music_tmp, sub_tmp)
        out_bytes = Path(out_tmp).read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"pro_edit_failed: {str(e)[:200]}")
    finally:
        for p in (src_tmp, out_tmp, logo_tmp, music_tmp, sub_tmp, base_tmp, insert_tmp):
            try:
                if p:
                    Path(p).unlink(missing_ok=True)
            except Exception:
                pass

    exp_id = parent["experience_id"]
    new_id = str(uuid.uuid4())
    path = f"{storage.APP_NAME}/cuts/{exp_id}/{new_id}.mp4"
    put = await asyncio.to_thread(storage.put_object, path, out_bytes, "video/mp4")
    version = await _next_version(exp_id)
    cut = {
        "id": new_id, "experience_id": exp_id, "owner": user["user_id"], "version": version,
        "parent_id": parent["id"], "kind": "pro-edit", "edl": parent.get("edl"),
        "music_id": body.music_id,
        "instruction": f"pro-edit · {body.aspect} · {body.filter} · {body.transition}",
        "edit_decisions": [{"type": "pro-edit", "description": {
            "en": f"Format {body.aspect}, {body.filter} look, {body.transition} transition"
                  + (", music" if body.music_id else "") + (", logo" if logo.get("enabled") else "")
                  + (", captions" if caps.get("enabled") else ""),
            "es": f"Formato {body.aspect}, look {body.filter}, transición {body.transition}"
                  + (", música" if body.music_id else "") + (", logo" if logo.get("enabled") else "")
                  + (", subtítulos" if caps.get("enabled") else "")}}],
        "status": "ready", "storage_path": put["path"], "created_at": now_iso(),
    }
    await db.cut_versions.insert_one(dict(cut))
    cut.pop("_id", None)
    cut["captions_status"] = captions_status
    cut["scene_transitions"] = bool(scene_transition and effective_transition == "none")
    return cut



# ---------- traceability ----------
@api.get("/experiences/{exp_id}/agent-runs")
async def agent_runs(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    return await db.agent_runs.find({"experience_id": exp_id}, {"_id": 0}).sort("created_at", 1).to_list(500)


# ---------- ORCHESTRATOR (primary differentiator) ----------
@api.get("/experiences/{exp_id}/orchestrator")
async def get_orchestrator(exp_id: str, user: dict = Depends(get_current_user)):
    """Recompute the live production state and return the Orchestrator's next
    best decision (Addendum §2). Recomputed on every call → deletion-aware."""
    exp = await get_experience(exp_id, user)
    return await orchestrator.orchestrate(exp)


@api.get("/experiences/{exp_id}/decisions")
async def orchestrator_decisions(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    return await db.orchestrator_decisions.find({"experience_id": exp_id}, {"_id": 0}).sort("created_at", -1).to_list(100)


# ---------- media deletion / Trash / recovery (Addendum §3) ----------
async def _cuts_using(exp_id: str, asset_id: str):
    cuts = await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0}).to_list(200)
    return [{"id": c["id"], "version": c.get("version"), "status": c.get("status")}
            for c in cuts if any(cl.get("asset_id") == asset_id for cl in (c.get("edl") or []))]


async def _beats_at_risk(exp: dict, asset_id: str):
    """Beats this asset covers that NO other active analyzed asset covers."""
    beats = (exp.get("plan") or {}).get("beats") or []
    assets = await db.media_assets.find(
        {"experience_id": exp["id"], "status": "analyzed"}, {"_id": 0}).to_list(300)

    def matched(a):
        an = a.get("analysis") or {}
        if not [s for s in (an.get("segments") or []) if s.get("usable", True)]:
            return set()
        return set((an.get("narrative_relevance") or {}).get("matched_beats") or [])

    target = next((a for a in assets if a["id"] == asset_id), None)
    if not target:
        return []
    others = set().union(*[matched(a) for a in assets if a["id"] != asset_id]) if len(assets) > 1 else set()
    risk = matched(target) - others
    return [{"id": b.get("id"), "name": b.get("name")} for b in beats if b.get("id") in risk]


@api.get("/media/{asset_id}/impact")
async def media_impact(asset_id: str, user: dict = Depends(get_current_user)):
    a = await db.media_assets.find_one({"id": asset_id, "owner": user["user_id"]}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    exp = await db.experiences.find_one({"id": a["experience_id"]}, {"_id": 0})
    cuts = await _cuts_using(a["experience_id"], asset_id)
    risk = await _beats_at_risk(exp, asset_id)
    en = "This clip is unused." if not cuts else f"This clip is used in {len(cuts)} cut(s)."
    es = "Este clip no se usa." if not cuts else f"Este clip se usa en {len(cuts)} corte(s)."
    if risk:
        en += " Deleting it creates a missing shot."
        es += " Borrarlo crea una toma faltante."
    return {"asset_id": asset_id, "cuts": cuts, "used_in_cuts": len(cuts),
            "beats_at_risk": risk, "message": {"en": en, "es": es}}


@api.delete("/media/{asset_id}")
async def delete_media(asset_id: str, permanent: bool = Query(default=False),
                       confirm: bool = Query(default=False), force: bool = Query(default=False),
                       user: dict = Depends(get_current_user)):
    a = await db.media_assets.find_one({"id": asset_id, "owner": user["user_id"]}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    exp_id = a["experience_id"]
    if permanent:
        if not confirm:
            raise HTTPException(status_code=400, detail="confirm_required")
        # Guard: don't silently orphan a cut's EDL. Require force to hard-delete a used clip.
        if not force and await _cuts_using(exp_id, asset_id):
            raise HTTPException(status_code=409, detail="in_use_requires_force")
        try:
            await asyncio.to_thread(storage.delete_object, a["storage_path"])
        except Exception:
            pass
        await db.media_assets.delete_one({"id": asset_id})
        dtype = "permanent"
    else:
        await db.media_assets.update_one(
            {"id": asset_id}, {"$set": {"status": "trashed", "prev_status": a.get("status"),
                                        "trashed_at": now_iso()}})
        dtype = "trash"
    impacted = await orchestrator.recompute_cut_impact(exp_id)
    await db.deletion_events.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "asset_id": asset_id,
        "experience_id": exp_id, "type": dtype, "impacted_cuts": impacted, "timestamp": now_iso()})
    exp = await db.experiences.find_one({"id": exp_id}, {"_id": 0})
    decision = await orchestrator.orchestrate(exp)
    return {"ok": True, "type": dtype, "impacted_cuts": impacted, "decision": decision}


@api.post("/media/{asset_id}/restore")
async def restore_media(asset_id: str, user: dict = Depends(get_current_user)):
    a = await db.media_assets.find_one({"id": asset_id, "owner": user["user_id"]}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    if a.get("status") != "trashed":
        raise HTTPException(status_code=400, detail="not_in_trash")
    await db.media_assets.update_one(
        {"id": asset_id}, {"$set": {"status": a.get("prev_status") or "analyzed"},
                           "$unset": {"trashed_at": ""}})
    # Un-stick the loop: clears impacted on cuts whose clips are all available again.
    await orchestrator.recompute_cut_impact(a["experience_id"])
    exp = await db.experiences.find_one({"id": a["experience_id"]}, {"_id": 0})
    decision = await orchestrator.orchestrate(exp)
    return {"ok": True, "decision": decision}


@api.delete("/cuts/{cut_id}")
async def delete_cut(cut_id: str, user: dict = Depends(get_current_user)):
    """Delete a rendered cut only — source media is preserved (Addendum §3.2)."""
    c = await db.cut_versions.find_one({"id": cut_id, "owner": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    if c.get("storage_path"):
        try:
            await asyncio.to_thread(storage.delete_object, c["storage_path"])
        except Exception:
            pass
    await db.cut_versions.delete_one({"id": cut_id})
    await db.deletion_events.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "cut_id": cut_id,
        "experience_id": c["experience_id"], "type": "cut", "timestamp": now_iso()})
    return {"ok": True, "message": {"en": "Cut deleted. Originals preserved.",
                                    "es": "Corte borrado. Originales preservados."}}


@api.get("/experiences/{exp_id}/impact")
async def experience_impact(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    videos = await db.media_assets.count_documents({"experience_id": exp_id, "status": {"$ne": "trashed"}})
    cuts = await db.cut_versions.count_documents({"experience_id": exp_id})
    return {"videos": videos, "cuts": cuts,
            "message": {"en": f"This will remove {videos} videos and {cuts} cuts and generated assets.",
                        "es": f"Esto quitará {videos} videos y {cuts} cortes y activos generados."}}


@api.delete("/experiences/{exp_id}")
async def delete_experience(exp_id: str, permanent: bool = Query(default=False),
                            confirm: bool = Query(default=False), user: dict = Depends(get_current_user)):
    exp = await get_experience(exp_id, user)
    if permanent:
        if not confirm:
            raise HTTPException(status_code=400, detail="confirm_required")
        for a in await db.media_assets.find({"experience_id": exp_id}, {"_id": 0, "storage_path": 1}).to_list(500):
            try:
                await asyncio.to_thread(storage.delete_object, a["storage_path"])
            except Exception:
                pass
        await db.media_assets.delete_many({"experience_id": exp_id})
        await db.cut_versions.delete_many({"experience_id": exp_id})
        await db.orchestrator_decisions.delete_many({"experience_id": exp_id})
        await db.experiences.delete_one({"id": exp_id})
        dtype = "experience_permanent"
    else:
        await db.media_assets.update_many({"experience_id": exp_id, "status": {"$ne": "trashed"}},
                                          {"$set": {"status": "trashed", "trashed_at": now_iso()}})
        await db.experiences.update_one({"id": exp_id}, {"$set": {"status": "trashed", "trashed_at": now_iso()}})
        dtype = "experience_trash"
    await db.deletion_events.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "experience_id": exp_id,
        "type": dtype, "timestamp": now_iso()})
    return {"ok": True, "type": dtype}


@api.post("/cuts/{cut_id}/remove-clip")
async def remove_clip_from_cut(cut_id: str, body: RemoveClipIn, background: BackgroundTasks,
                               user: dict = Depends(get_current_user)):
    """Remove a clip from a cut WITHOUT deleting the original → new CutVersion (Addendum §4.1, EDIT-01)."""
    parent = await db.cut_versions.find_one({"id": cut_id, "owner": user["user_id"]}, {"_id": 0})
    if not parent:
        raise HTTPException(status_code=404, detail="Cut not found")
    new_edl = [c for c in (parent.get("edl") or []) if c.get("asset_id") != body.asset_id]
    if not new_edl:
        raise HTTPException(status_code=400, detail="would_be_empty")
    if len(new_edl) == len(parent.get("edl") or []):
        raise HTTPException(status_code=400, detail="clip_not_in_cut")
    for i, c in enumerate(new_edl):
        c["order"] = i
    exp_id = parent["experience_id"]
    version = await _next_version(exp_id)
    cut = {
        "id": str(uuid.uuid4()), "experience_id": exp_id, "owner": user["user_id"],
        "version": version, "parent_id": parent["id"], "kind": "edit",
        "instruction": f"remove clip {body.asset_id}", "edl": new_edl,
        "music_id": parent.get("music_id"),
        "edit_decisions": [{"type": "remove", "description": {"en": "Removed a clip from the cut.",
                                                              "es": "Se quitó un clip del corte."}}],
        "status": "rendering", "storage_path": None, "created_at": now_iso(),
    }
    await db.cut_versions.insert_one(dict(cut))
    cut.pop("_id", None)
    background.add_task(render_cut_task, exp_id, cut["id"])
    return cut


# ---------- account / pricing / usage ----------
async def compute_usage(user: dict) -> dict:
    uid = user["user_id"]
    exp_count = await db.experiences.count_documents({"owner": uid})
    cut_count = await db.cut_versions.count_documents({"owner": uid})
    gen_count = await video_used_this_month(uid)
    return {"experiences": exp_count, "cuts": cut_count, "ai_generations": gen_count}


async def video_used_this_month(uid: str) -> int:
    ym = datetime.now(timezone.utc).strftime("%Y-%m")
    return await db.video_jobs.count_documents(
        {"owner": uid, "kind": "generate", "created_at": {"$regex": f"^{ym}"}})


@api.get("/account")
async def get_account(user: dict = Depends(get_current_user)):
    plan_id = user.get("plan") or "free"
    plan = await plans_store.get_plan(plan_id)
    usage = await compute_usage(user)
    return {"user": {k: user.get(k) for k in ("user_id", "email", "name", "picture")},
            "is_admin": user.get("is_admin", False),
            "plan": plan, "usage": usage, "limits": plan["limits"],
            "entitlements": plan.get("entitlements", {})}


@api.get("/pricing/plans")
async def pricing_plans(user: dict = Depends(get_current_user)):
    return {"plans": await plans_store.list_plans(), "faq": plan_catalog.FAQ,
            "current_plan": user.get("plan") or "free", "version": plan_catalog.PLANS_VERSION}


@api.post("/account/plan")
async def set_plan(body: PlanIn2, user: dict = Depends(get_current_user)):
    plan = await plans_store.get_plan(body.plan)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"plan": plan["id"]}})
    return {"ok": True, "plan": plan}


# ---------- stock music (CC0) ----------
@api.get("/music")
async def get_music(user: dict = Depends(get_current_user)):
    return await music_lib.list_tracks()


# ---------- AI video (Vertex/Veo via Cloud Run gateway) ----------
@api.get("/video/health")
async def video_health():
    return vertex_video.status()


async def _refresh_job(job: dict) -> dict:
    """Poll the gateway for a RUNNING job and persist status transitions."""
    op = job.get("operation_name")
    if job.get("status") not in ("RUNNING", "QUEUED") or not op:
        return job
    try:
        st = await asyncio.to_thread(vertex_video.poll, op, job.get("output_prefix"))
    except Exception as e:
        await db.video_jobs.update_one({"id": job["id"]}, {"$set": {"last_error": str(e)[:200]}})
        return job
    upd = {}
    if st.get("done"):
        if st.get("status") == "DONE" and st.get("gcs_uri"):
            upd = {"status": "DONE", "gcs_uri": st["gcs_uri"],
                   "download_url": f"/api/video/{job['id']}/download", "completed_at": now_iso()}
        else:
            upd = {"status": "FAILED", "error": st.get("error", "failed")}
    else:
        upd = {"status": "RUNNING", "progress": st.get("progress")}
    await db.video_jobs.update_one({"id": job["id"]}, {"$set": upd})
    return {**job, **upd}


@api.post("/video/generate")
async def video_generate(body: VideoGenIn, user: dict = Depends(get_current_user)):
    plan = await plans_store.get_plan(user.get("plan") or "free")
    if not (plan.get("entitlements") or {}).get("video"):
        raise HTTPException(status_code=403, detail="video_not_entitled")
    quota = (plan.get("limits") or {}).get("ai_generations", 0)
    used = await video_used_this_month(user["user_id"])
    if used >= quota:
        raise HTTPException(status_code=403, detail="quota_exceeded")
    if not vertex_video.connected:
        raise HTTPException(status_code=503, detail="veo_gateway_not_configured")
    try:
        sub = await asyncio.to_thread(vertex_video.submit, body.prompt, body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"veo_submit_failed: {str(e)[:200]}")
    job = {
        "id": str(uuid.uuid4()),
        "owner": user["user_id"],
        "kind": "generate",
        "prompt": body.prompt,
        "options": body.model_dump(),
        "operation_name": sub.get("operation_name"),
        "output_prefix": sub.get("output_prefix"),
        "model": sub.get("model"),
        "status": "RUNNING",
        "created_at": now_iso(),
    }
    await db.video_jobs.insert_one(dict(job))
    job.pop("_id", None)
    return job


@api.get("/video/jobs")
async def video_jobs(user: dict = Depends(get_current_user)):
    jobs = await db.video_jobs.find({"owner": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    refreshed = await asyncio.gather(*[_refresh_job(j) for j in jobs])
    return list(refreshed)


@api.delete("/video/jobs/{job_id}")
async def delete_video_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete an entire AI-generated video (job record)."""
    job = await db.video_jobs.find_one({"id": job_id, "owner": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    await db.video_jobs.delete_one({"id": job_id})
    await db.deletion_events.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "video_job_id": job_id,
        "type": "video_generation", "timestamp": now_iso()})
    return {"ok": True}


# ---------- Pro editor (Phase a) — reframe / filter / speed / logo ----------
class LogoOpts(BaseModel):
    enabled: bool = False
    x: float = 0.95
    y: float = 0.95
    scale: float = 0.18
    opacity: float = 0.85


class VideoEditIn(BaseModel):
    aspect: str = "16:9"
    filter: str = "none"
    speed: float = 1.0
    logo: Optional[LogoOpts] = None
    transition: str = "none"
    captions: Optional[dict] = None


class PrefsIn(BaseModel):
    logo: Optional[LogoOpts] = None


@api.post("/me/logo")
async def upload_logo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="logo_too_large")
    path = f"{storage.APP_NAME}/logos/{user['user_id']}.png"
    await asyncio.to_thread(storage.put_object, path, data, "image/png")
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"preferences.logo_path": path, "preferences.has_logo": True}})
    return {"ok": True, "logo_url": "/api/me/logo"}


@api.get("/me/logo")
async def get_logo(authorization: str = Header(default=None), auth: str = Query(default=None)):
    token = auth or (authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await _verify_token(token)
    u = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    lp = (u.get("preferences") or {}).get("logo_path")
    if not lp:
        raise HTTPException(status_code=404, detail="no_logo")
    data, ct = await asyncio.to_thread(storage.get_object, lp)
    return Response(content=data, media_type="image/png")


@api.get("/me/preferences")
async def get_prefs(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    prefs = u.get("preferences") or {}
    return {"logo": prefs.get("logo"), "has_logo": prefs.get("has_logo", False)}


@api.put("/me/preferences")
async def put_prefs(body: PrefsIn, user: dict = Depends(get_current_user)):
    if body.logo is not None:
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"preferences.logo": body.logo.model_dump()}})
    return {"ok": True}


@api.post("/video/jobs/{job_id}/edit")
async def edit_video(job_id: str, body: VideoEditIn, user: dict = Depends(get_current_user)):
    job = await db.video_jobs.find_one({"id": job_id, "owner": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    if job.get("status") != "DONE":
        raise HTTPException(status_code=400, detail="job_not_ready")
    # Source bytes: from a previous edit (object storage) or the Veo output (GCS via gateway).
    if job.get("edited_path"):
        src_bytes = (await asyncio.to_thread(storage.get_object, job["edited_path"]))[0]
    elif job.get("gcs_uri"):
        src_bytes = await asyncio.to_thread(vertex_video.download, job["gcs_uri"])
    else:
        raise HTTPException(status_code=400, detail="no_source")

    logo_tmp = None
    opts = body.model_dump()
    if body.logo and body.logo.enabled:
        u = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        lp = (u.get("preferences") or {}).get("logo_path")
        if lp:
            logo_bytes = (await asyncio.to_thread(storage.get_object, lp))[0]
            logo_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            Path(logo_tmp).write_bytes(logo_bytes)
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"preferences.logo": body.logo.model_dump()}})

    src_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    Path(src_tmp).write_bytes(src_bytes)
    caps = body.captions or {}
    sub_tmp = None
    captions_status = "off"
    if caps.get("enabled"):
        W, H = video_editor.ASPECT_DIMS.get(body.aspect, video_editor.ASPECT_DIMS["16:9"])
        try:
            sub_tmp = await captions.generate_ass(src_tmp, W, H, float(body.speed or 1),
                                                  caps.get("style", "bold"), caps.get("lang") or None)
        except Exception as e:
            logger.warning(f"captions failed (video): {e}")
        captions_status = "applied" if sub_tmp else "no_speech"
    try:
        await asyncio.to_thread(video_editor.transform_video, src_tmp, out_tmp, opts, logo_tmp, None, sub_tmp)
        out_bytes = Path(out_tmp).read_bytes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"edit_failed: {str(e)[:200]}")
    finally:
        for p in (src_tmp, out_tmp, logo_tmp, sub_tmp):
            try:
                if p:
                    Path(p).unlink(missing_ok=True)
            except Exception:
                pass

    new_id = str(uuid.uuid4())
    edited_path = f"{storage.APP_NAME}/edits/{user['user_id']}/{new_id}.mp4"
    await asyncio.to_thread(storage.put_object, edited_path, out_bytes, "video/mp4")
    new_job = {
        "id": new_id, "owner": user["user_id"], "kind": "edit", "parent_job": job_id,
        "prompt": f"{job.get('prompt', 'edit')} · {body.aspect} · {body.filter}",
        "options": {"aspect_ratio": body.aspect, "duration_sec": job.get("options", {}).get("duration_sec"),
                    "filter": body.filter, "speed": body.speed},
        "edited_path": edited_path, "status": "DONE",
        "download_url": f"/api/video/{new_id}/download", "created_at": now_iso(),
    }
    await db.video_jobs.insert_one(dict(new_job))
    new_job.pop("_id", None)
    new_job["captions_status"] = captions_status
    return new_job


@api.get("/video/{job_id}/download")
async def video_download(job_id: str, request: Request, authorization: str = Header(default=None), auth: str = Query(default=None)):
    token = auth or (authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await _verify_token(token)
    job = await db.video_jobs.find_one({"id": job_id, "owner": session["user_id"]}, {"_id": 0})
    if not job or job.get("status") != "DONE":
        raise HTTPException(status_code=404, detail="Video not ready")
    if job.get("edited_path"):
        data = (await asyncio.to_thread(storage.get_object, job["edited_path"]))[0]
    elif job.get("gcs_uri"):
        data = await asyncio.to_thread(vertex_video.download, job["gcs_uri"])
    else:
        raise HTTPException(status_code=404, detail="Video not ready")
    return _ranged_video_response(data, request.headers.get("range"))


def _ranged_video_response(data: bytes, range_header: str = None):
    """Serve mp4 with HTTP Range support so browsers can seek/play (206 Partial Content)."""
    total = len(data)
    base_headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}
    if range_header and range_header.startswith("bytes="):
        try:
            rng = range_header.split("=", 1)[1].split(",")[0]
            start_s, _, end_s = rng.partition("-")
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else total - 1
            end = min(end, total - 1)
            if start > end or start >= total:
                raise ValueError
        except ValueError:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{total}"})
        chunk = data[start:end + 1]
        headers = {**base_headers, "Content-Range": f"bytes {start}-{end}/{total}",
                   "Content-Length": str(len(chunk))}
        return Response(content=chunk, status_code=206, media_type="video/mp4", headers=headers)
    return Response(content=data, media_type="video/mp4",
                    headers={**base_headers, "Content-Length": str(total)})


# ---------- file streaming ----------
async def _verify_token(token: str) -> dict:
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    return session

@api.get("/files/{path:path}")
async def get_file(path: str, request: Request, authorization: str = Header(default=None), auth: str = Query(default=None),
                   session_token: str = None):
    token = auth
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await _verify_token(token)
    uid = session["user_id"]
    owned = await db.media_assets.find_one({"storage_path": path, "owner": uid}, {"_id": 0}) or \
        await db.cut_versions.find_one({"storage_path": path, "owner": uid}, {"_id": 0})
    if not owned:
        raise HTTPException(status_code=404, detail="Not found")
    data, ct = await asyncio.to_thread(storage.get_object, path)
    content_type = owned.get("content_type") or ct or "application/octet-stream"
    # Videos need HTTP Range support so browsers can decode/seek (mp4 moov-at-end otherwise renders black).
    if str(content_type).startswith("video/") or path.lower().endswith((".mp4", ".mov", ".webm", ".m4v")):
        return _ranged_video_response(data, request.headers.get("range"))
    return Response(content=data, media_type=content_type)


@app.on_event("startup")
async def startup():
    try:
        await asyncio.to_thread(storage.init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    try:
        await music_lib.seed_music()
        logger.info("Music library seeded")
    except Exception as e:
        logger.error(f"Music seed failed: {e}")


app.include_router(api)
app.include_router(admin_router)
app.include_router(payments_router)
app.include_router(inserts_router)
app.include_router(v2_router)
app.include_router(public_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

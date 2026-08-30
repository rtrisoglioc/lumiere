import os
import uuid
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Header, Query, BackgroundTasks
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from db import db, now_iso, WORKDIR
import storage
import ffmpeg_worker as ff
from agent_adapter import agent_builder
from partner_adapter import partner
from vertex_video_adapter import vertex_video
import plans as plan_catalog
import music as music_lib
import agents
from auth import exchange_session, get_current_user, logout as do_logout

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

class PlanIn(BaseModel):
    intent: str

class ReviseIn(BaseModel):
    instruction: str
    music_id: str = None

class CutIn(BaseModel):
    music_id: str = None

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
                        samesite="none", path="/", max_age=7 * 24 * 3600)
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
    exp = {
        "id": str(uuid.uuid4()),
        "owner": user["user_id"],
        "title": body.title,
        "type": body.type,
        "language": body.language,
        "visibility": "private",
        "stage": "intent",
        "intent": None,
        "plan": None,
        "missions": None,
        "completeness": None,
        "created_at": now_iso(),
    }
    await db.experiences.insert_one(dict(exp))
    exp.pop("_id", None)
    return exp

@api.get("/experiences")
async def list_experiences(user: dict = Depends(get_current_user)):
    return await db.experiences.find({"owner": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)

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


# ---------- traceability ----------
@api.get("/experiences/{exp_id}/agent-runs")
async def agent_runs(exp_id: str, user: dict = Depends(get_current_user)):
    await get_experience(exp_id, user)
    return await db.agent_runs.find({"experience_id": exp_id}, {"_id": 0}).sort("created_at", 1).to_list(500)


# ---------- account / pricing / usage ----------
async def compute_usage(user: dict) -> dict:
    uid = user["user_id"]
    exp_count = await db.experiences.count_documents({"owner": uid})
    cut_count = await db.cut_versions.count_documents({"owner": uid})
    gen_count = await db.video_jobs.count_documents({"owner": uid})
    return {"experiences": exp_count, "cuts": cut_count, "ai_generations": gen_count}


@api.get("/account")
async def get_account(user: dict = Depends(get_current_user)):
    plan_id = user.get("plan") or "free"
    plan = plan_catalog.get_plan(plan_id)
    usage = await compute_usage(user)
    return {"user": {k: user.get(k) for k in ("user_id", "email", "name", "picture")},
            "plan": plan, "usage": usage, "limits": plan["limits"]}


@api.get("/pricing/plans")
async def pricing_plans(user: dict = Depends(get_current_user)):
    return {"plans": plan_catalog.PLANS, "faq": plan_catalog.FAQ,
            "current_plan": user.get("plan") or "free", "version": plan_catalog.PLANS_VERSION}


@api.post("/account/plan")
async def set_plan(body: PlanIn2, user: dict = Depends(get_current_user)):
    plan = plan_catalog.get_plan(body.plan)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"plan": plan["id"]}})
    return {"ok": True, "plan": plan}


# ---------- stock music (CC0) ----------
@api.get("/music")
async def get_music(user: dict = Depends(get_current_user)):
    return await music_lib.list_tracks()


# ---------- AI video (Vertex/Veo — mocked adapter) ----------
@api.get("/video/health")
async def video_health():
    return vertex_video.status()


@api.post("/video/generate")
async def video_generate(body: VideoGenIn, user: dict = Depends(get_current_user)):
    result = vertex_video.generate(body.prompt, body.model_dump())
    job = {
        "id": str(uuid.uuid4()),
        "owner": user["user_id"],
        "kind": "generate",
        "prompt": body.prompt,
        "options": body.model_dump(),
        "status": result["status"],
        "result": result,
        "created_at": now_iso(),
    }
    await db.video_jobs.insert_one(dict(job))
    job.pop("_id", None)
    return job


@api.post("/video/enhance")
async def video_enhance(body: VideoEnhanceIn, user: dict = Depends(get_current_user)):
    result = vertex_video.enhance(body.asset_id, body.model_dump())
    job = {
        "id": str(uuid.uuid4()),
        "owner": user["user_id"],
        "kind": "enhance",
        "asset_id": body.asset_id,
        "options": body.model_dump(),
        "status": result["status"],
        "result": result,
        "created_at": now_iso(),
    }
    await db.video_jobs.insert_one(dict(job))
    job.pop("_id", None)
    return job


@api.get("/video/jobs")
async def video_jobs(user: dict = Depends(get_current_user)):
    return await db.video_jobs.find({"owner": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


# ---------- file streaming ----------
async def _verify_token(token: str) -> dict:
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    return session

@api.get("/files/{path:path}")
async def get_file(path: str, authorization: str = Header(default=None), auth: str = Query(default=None),
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
    return Response(content=data, media_type=owned.get("content_type", ct))


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
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

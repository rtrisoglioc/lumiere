"""Admin panel API — admin-only (require_admin). Manages plans/pricing & quotas,
users, video jobs, social posts and site settings. Everything configurable at
runtime and persisted in MongoDB."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db, now_iso
from auth import require_admin, is_admin_email
import plans_store

admin_router = APIRouter(prefix="/api/admin")


class PlansIn(BaseModel):
    plans: list


class UserPlanIn(BaseModel):
    plan: str


class SettingsIn(BaseModel):
    settings: dict


@admin_router.get("/overview")
async def overview(_: dict = Depends(require_admin)):
    return {
        "users": await db.users.count_documents({}),
        "experiences": await db.experiences.count_documents({}),
        "cuts": await db.cut_versions.count_documents({}),
        "video_jobs": await db.video_jobs.count_documents({}),
        "social_posts": await db.social_posts.count_documents({}),
        "video_done": await db.video_jobs.count_documents({"status": "DONE"}),
        "video_failed": await db.video_jobs.count_documents({"status": "FAILED"}),
    }


@admin_router.get("/plans")
async def get_plans(_: dict = Depends(require_admin)):
    return {"plans": await plans_store.list_plans()}


@admin_router.put("/plans")
async def put_plans(body: PlansIn, _: dict = Depends(require_admin)):
    if not body.plans:
        raise HTTPException(status_code=400, detail="plans required")
    return {"plans": await plans_store.save_plans(body.plans)}


@admin_router.get("/users")
async def list_users(_: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for u in users:
        u["is_admin"] = is_admin_email(u.get("email"))
        u["experiences"] = await db.experiences.count_documents({"owner": u["user_id"]})
        u["video_jobs"] = await db.video_jobs.count_documents({"owner": u["user_id"]})
        u["plan"] = u.get("plan") or "free"
    return users


@admin_router.post("/users/{user_id}/plan")
async def set_user_plan(user_id: str, body: UserPlanIn, _: dict = Depends(require_admin)):
    plan = await plans_store.get_plan(body.plan)
    await db.users.update_one({"user_id": user_id}, {"$set": {"plan": plan["id"]}})
    return {"ok": True, "user_id": user_id, "plan": plan["id"]}


@admin_router.get("/video-jobs")
async def video_jobs(_: dict = Depends(require_admin)):
    return await db.video_jobs.find({}, {"_id": 0, "result": 0}).sort("created_at", -1).to_list(200)


@admin_router.get("/social-posts")
async def social_posts(_: dict = Depends(require_admin)):
    return await db.social_posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)


@admin_router.get("/settings")
async def get_settings(_: dict = Depends(require_admin)):
    doc = await db.site_config.find_one({"key": "settings"}, {"_id": 0})
    return {"settings": (doc or {}).get("settings", {})}


@admin_router.put("/settings")
async def put_settings(body: SettingsIn, _: dict = Depends(require_admin)):
    await db.site_config.update_one(
        {"key": "settings"}, {"$set": {"key": "settings", "settings": body.settings, "updated_at": now_iso()}},
        upsert=True)
    return {"settings": body.settings}

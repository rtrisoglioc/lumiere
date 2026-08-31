"""DB-backed plan catalog. Admin edits are stored in site_config; falls back to
the plans.py defaults when no override exists. Keeps prices/quotas configurable
at runtime from the Admin panel."""
from db import db
import plans as defaults

CONFIG_KEY = "plans"


async def list_plans() -> list:
    doc = await db.site_config.find_one({"key": CONFIG_KEY}, {"_id": 0})
    if doc and isinstance(doc.get("plans"), list) and doc["plans"]:
        return doc["plans"]
    return defaults.PLANS


async def get_plan(plan_id: str) -> dict:
    for p in await list_plans():
        if p["id"] == plan_id:
            return p
    plans = await list_plans()
    return plans[0]


async def save_plans(plans: list) -> list:
    await db.site_config.update_one(
        {"key": CONFIG_KEY}, {"$set": {"key": CONFIG_KEY, "plans": plans}}, upsert=True)
    return plans

"""PayPal payments (REST v2) for subscription plan upgrades.

Sandbox/live selected via PAYPAL_MODE. The charge amount is computed
server-side from the plan catalog — never trusted from the client. On a
COMPLETED capture the user's plan is upgraded and a payment record is stored."""
import os
import uuid
import asyncio

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from db import db, now_iso
from auth import get_current_user
import plans_store

load_dotenv()
payments_router = APIRouter(prefix="/api/payments")

CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
SECRET = os.environ.get("PAYPAL_SECRET")
MODE = (os.environ.get("PAYPAL_MODE") or "sandbox").strip().lower()
BASE = "https://api-m.paypal.com" if MODE == "live" else "https://api-m.sandbox.paypal.com"


def _configured() -> bool:
    return bool(CLIENT_ID and SECRET)


def _token() -> str:
    r = requests.post(f"{BASE}/v1/oauth2/token",
                      data={"grant_type": "client_credentials"},
                      auth=(CLIENT_ID, SECRET), timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _create_order_sync(reference: str, description: str, amount: float) -> dict:
    tok = _token()
    r = requests.post(
        f"{BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json={"intent": "CAPTURE", "purchase_units": [{
            "reference_id": reference,
            "description": description,
            "amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}]},
        timeout=30)
    r.raise_for_status()
    return r.json()


def _capture_sync(order_id: str) -> dict:
    tok = _token()
    r = requests.post(
        f"{BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        timeout=30)
    r.raise_for_status()
    return r.json()


def _captured_amount(data: dict):
    """Extract the actually-captured amount from a v2 capture response."""
    try:
        cap = data["purchase_units"][0]["payments"]["captures"][0]["amount"]
        return float(cap["value"]), cap.get("currency_code", "USD")
    except Exception:
        return None, None


class CreateIn(BaseModel):
    plan: str
    cycle: str = "monthly"


class CaptureIn(BaseModel):
    order_id: str
    plan: str
    cycle: str = "monthly"


async def _plan_amount(plan_id: str, cycle: str):
    plan = await plans_store.get_plan(plan_id)
    price = (plan.get("price") or {}).get("yearly" if cycle == "yearly" else "monthly", 0)
    return plan, float(price or 0)


@payments_router.get("/config")
async def config():
    return {"provider": "paypal", "mode": MODE, "enabled": _configured(),
            "client_id": CLIENT_ID or "", "currency": "USD"}


@payments_router.post("/paypal/create-order")
async def create_order(body: CreateIn, user: dict = Depends(get_current_user)):
    if not _configured():
        raise HTTPException(status_code=503, detail="paypal_not_configured")
    plan, amount = await _plan_amount(body.plan, body.cycle)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="plan_not_payable")
    try:
        data = await asyncio.to_thread(
            _create_order_sync, f"{user['user_id']}:{body.plan}:{body.cycle}",
            f"LUMIERE {plan['name']} ({body.cycle})", amount)
    except requests.HTTPError as e:
        msg = e.response.text[:200] if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=f"paypal_create_failed: {msg}")
    return {"id": data["id"], "amount": amount, "currency": "USD"}


@payments_router.post("/paypal/capture")
async def capture(body: CaptureIn, user: dict = Depends(get_current_user)):
    if not _configured():
        raise HTTPException(status_code=503, detail="paypal_not_configured")
    plan, amount = await _plan_amount(body.plan, body.cycle)
    try:
        data = await asyncio.to_thread(_capture_sync, body.order_id)
    except requests.HTTPError as e:
        msg = e.response.text[:200] if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=f"paypal_capture_failed: {msg}")
    status = data.get("status")
    if status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"payment_not_completed: {status}")
    paid, currency = _captured_amount(data)
    if paid is None or abs(paid - amount) > 0.01 or currency != "USD":
        raise HTTPException(status_code=400, detail="amount_mismatch")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"plan": plan["id"]}})
    rec = {"id": str(uuid.uuid4()), "user_id": user["user_id"], "provider": "paypal",
           "order_id": body.order_id, "plan": plan["id"], "cycle": body.cycle,
           "amount": paid, "currency": currency, "status": status, "created_at": now_iso()}
    await db.payments.insert_one(dict(rec))
    rec.pop("_id", None)
    return {"ok": True, "plan": plan, "payment": rec}


@payments_router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    return await db.payments.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)

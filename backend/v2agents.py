"""v2.0 agents — exact system prompts from the Build Command v2.0.

All outputs are structured JSON (English). These call the LLM DIRECTLY via the
Emergent Universal Key (emergentintegrations) so the exact prompts/schemas are
honored — they intentionally BYPASS the Agent Engine gateway, whose deployed
subagents use a different (bilingual, legacy) schema. Each call persists an
AgentRun for the Agent Trace. Deterministic guards live in code, not the model.
"""
import os
import re
import json
import time
import uuid
import hashlib

from agents import _persist_run
from db import db

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL_FAST = "gemini-3.5-flash"
MODEL_PRO = "gemini-3.5-flash"
PROXY_FAST = MODEL_FAST  # kept for call-site compatibility
FUNCTIONS = ["arrival", "discovery", "movement", "connection", "reflection", "resolution"]
DEMO_MODE = (os.environ.get("DEMO_MODE") or "").lower() in ("1", "true", "yes")


def _extract_json(text):
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str):
        return None
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    cand = fence.group(1) if fence else text
    s, e = cand.find("{"), cand.rfind("}")
    if s != -1 and e != -1 and e > s:
        cand = cand[s:e + 1]
    try:
        return json.loads(cand)
    except Exception:
        return None


async def _run_and_trace(exp_id, agent_label, operation, system, prompt, model=None, files=None):
    from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
    started = time.time()
    status, out = "OK", None
    try:
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"{exp_id}:{operation}:{uuid.uuid4().hex[:8]}",
                       system_message=system).with_model("gemini", model or MODEL_FAST)
        fc = [FileContentWithMimeType(file_path=f["path"], mime_type=f["mime"]) for f in (files or [])] or None
        msg = UserMessage(text=prompt, file_contents=fc) if fc else UserMessage(text=prompt)
        raw = await chat.send_message(msg)
        out = _extract_json(raw)
    except Exception as e:
        status = "FAILED"
        out = {"_error": str(e)[:200]}
    latency_ms = int((time.time() - started) * 1000)
    # DEMO_MODE fail-safe: cache successes; reuse the last good response on failure for the same input.
    if DEMO_MODE:
        ckey = hashlib.sha256(f"{operation}|{prompt}".encode()).hexdigest()[:32]
        if status == "OK" and isinstance(out, dict) and not out.get("_error"):
            await db.demo_agent_cache.update_one({"key": ckey}, {"$set": {"key": ckey, "output": out}}, upsert=True)
        elif status == "FAILED":
            cached = await db.demo_agent_cache.find_one({"key": ckey}, {"_id": 0})
            if cached and cached.get("output"):
                out, status = cached["output"], "OK_CACHED"
    conf = out.get("confidence") if isinstance(out, dict) else None
    meta = {"service": "emergent-proxy", "operation": operation, "status": status,
            "provider": "google", "model": model or MODEL_FAST, "latency_ms": latency_ms,
            "confidence": conf if conf is not None else 0.85}
    await _persist_run(exp_id, agent_label, meta, operation, out if isinstance(out, dict) else {}, [
        {"name": "gemini.generate", "status": status, "latency_ms": latency_ms}])
    return out, meta


DIRECTOR_SYS = """You are the Director Agent of LUMIÈRE, a cinematic story planning system.
Given a real-world experience and the creator's emotional intent, produce a
short film structure of 5 to 7 narrative beats.

Rules:
- Beats must be filmable in the real location and timeframe given.
- Every beat has one narrative function from: arrival, discovery, movement,
  connection, reflection, resolution.
- Exactly 3 beats must be marked criticality="critical". The rest are "supporting".
- The arc must have a beginning, a change, and a close.
- Never invent events the creator did not describe. Plan opportunities, not fiction.
- suggested_title_card is a maximum of 4 words, editorial tone, or null.

Return ONLY valid JSON matching this schema, no prose, no markdown fences:
{"title":string,"premise":string,"arc_summary":string,"beats":[{"sequence":int,
"function":string,"label":string,"purpose":string,"criticality":string,
"suggested_title_card":string|null}]}"""


def _fallback_story(exp):
    loc = exp.get("location_name") or exp.get("title") or "the place"
    fns = ["arrival", "discovery", "movement", "connection", "reflection", "resolution"]
    beats = []
    for i, fn in enumerate(fns):
        beats.append({
            "sequence": i + 1, "function": fn,
            "label": f"{fn.capitalize()} at {loc}",
            "purpose": f"Show the {fn} moment of the experience at {loc}.",
            "criticality": "critical" if i in (0, 2, 5) else "supporting",
            "suggested_title_card": None,
        })
    return {"title": exp.get("title") or "Untitled", "premise": f"A short film about {loc}.",
            "arc_summary": "Arrival, a change in the middle, and a close.", "beats": beats}


def _enforce_three_critical(beats):
    for b in beats:
        if b.get("function") not in FUNCTIONS:
            b["function"] = "discovery"
    crit = [b for b in beats if b.get("criticality") == "critical"]
    if len(crit) == 3:
        return beats
    # deterministic: pick arrival-ish first, a middle, and resolution as critical
    order = sorted(beats, key=lambda b: b.get("sequence", 0))
    for b in order:
        b["criticality"] = "supporting"
    picks = set()
    if order:
        picks.add(order[0]["sequence"])
        picks.add(order[len(order) // 2]["sequence"])
        picks.add(order[-1]["sequence"])
    # ensure exactly 3
    seqs = [b["sequence"] for b in order]
    for s in seqs:
        if len(picks) >= 3:
            break
        picks.add(s)
    for b in order:
        if b["sequence"] in list(picks)[:3]:
            b["criticality"] = "critical"
    # trim if more than 3 got flagged
    crit_now = [b for b in order if b["criticality"] == "critical"]
    for extra in crit_now[3:]:
        extra["criticality"] = "supporting"
    return order


async def director_story(exp, intent):
    prompt = (
        f"Experience: {json.dumps({'title': exp.get('title'), 'location_name': exp.get('location_name'), 'type': exp.get('type'), 'start_date': exp.get('start_date'), 'end_date': exp.get('end_date'), 'target_platform': exp.get('target_platform')})}\n"
        f"Creator intent: {json.dumps({'feeling_tags': intent.get('feeling_tags'), 'free_text': intent.get('free_text'), 'creator_presence': intent.get('creator_presence'), 'desired_outcome': intent.get('desired_outcome')})}"
    )
    out, meta = await _run_and_trace(exp["id"], "Director Agent", "generate_story", DIRECTOR_SYS, prompt, model=PROXY_FAST)
    if not isinstance(out, dict) or not out.get("beats"):
        out, meta = await _run_and_trace(exp["id"], "Director Agent", "generate_story", DIRECTOR_SYS, prompt, model=PROXY_FAST)
    if not isinstance(out, dict) or not out.get("beats"):
        out = _fallback_story(exp)
    out["beats"] = _enforce_three_critical(out.get("beats") or [])
    return out, meta


CINE_SYS = """You are the Cinematographer Agent of LUMIÈRE.
Convert story beats into executable shot missions for a non-professional
creator using a phone camera.

Rules:
- Each mission must be executable in under 90 seconds of real effort.
- action must be a physical instruction, not a creative adjective.
  GOOD: "Walk through the entrance doorway while holding the phone at chest
  height, keep walking for 6 seconds."
  BAD: "Capture the feeling of arrival."
- duration_seconds between 4 and 10.
- ideal_time_window must be realistic for the shot's light needs.
- narrative_purpose explains in one sentence what the edit will use it for.
- priority 1 is highest. Critical beats get priority 1-3.

Return ONLY valid JSON: {"shots":[{"beat_sequence":int,"shot_type":string,
"action":string,"movement":string,"composition_note":string,
"duration_seconds":int,"ideal_time_window":string,"narrative_purpose":string,
"priority":int}]}"""


async def cinematographer_shots(exp, beats):
    beats_min = [{"sequence": b["sequence"], "function": b["function"], "label": b["label"],
                  "purpose": b["purpose"], "criticality": b["criticality"]} for b in beats]
    prompt = (f"Location: {exp.get('location_name')}. Target platform: {exp.get('target_platform')}.\n"
              f"Story beats: {json.dumps(beats_min)}\n"
              "Generate 8-12 shot missions. Each critical beat gets at least 2 shots; "
              "each supporting beat at least 1.")
    out, meta = await _run_and_trace(exp["id"], "Cinematographer", "generate_shots", CINE_SYS, prompt, model=PROXY_FAST)
    return out, meta


VISION_SYS = """You are the Vision Agent of LUMIÈRE. Analyze this video clip and segment it
into usable pieces for a cinematic edit.

For each segment you identify:
- start_sec / end_sec (segments are 2-10 seconds, do not overlap)
- scene_summary: one factual sentence of what is visible
- usability_score 0-1: technical quality (stability, exposure, focus, framing)
- narrative_relevance 0-1: how strongly it serves the story beats provided
- emotion_tags: up to 3 from curiosity, calm, energy, intimacy, freedom,
  wonder, resolution
- quality_flags: any of shaky, dark, overexposed, blurry, good
- has_people: boolean
- beat_candidates: which of the provided beat_ids this segment could serve

Story beats available: {beats_json}

Return ONLY valid JSON: {"segments":[...]}"""


async def vision_analyze(exp, beats, file_ref):
    beats_json = json.dumps([{"beat_id": b["beat_id"], "function": b["function"], "label": b["label"]} for b in beats])
    system = VISION_SYS.replace("{beats_json}", beats_json)
    out, meta = await _run_and_trace(exp["id"], "Vision Agent", "analyze_clip", system,
                                     "Analyze the attached clip and return the segments JSON.",
                                     files=[{"path": file_ref["path"], "mime": file_ref["mime"]}])
    return out, meta


EDITOR_SYS = """You are the Editor Agent of LUMIÈRE. Build an edit decision list for a short
cinematic film from the analyzed segments provided.

Hard rules:
- NEVER include a segment whose asset provenance is "ai_previz".
- Never include two segments marked as duplicates of each other.
- Order segments to follow the story beat sequence, not the capture order.
- Total duration must be within 15% of target_duration.
- Prefer segments with usability_score >= 0.6. Only use lower if a critical
  beat has no alternative.
- Open with an establishing or atmosphere segment. Close with the segment
  serving the resolution beat.
- Assign title_card only where the beat has a suggested_title_card and it
  adds clarity. Maximum 3 title cards per film.

Style targets:
- cinematic: 45s, average shot 3.5-5s, dissolve transitions, slow rhythm
- social: 22s, average shot 1.2-2s, hard cuts, open with strongest hook
- story: 55s, average shot 3s, explicit beginning-change-close, hard cuts

Return ONLY valid JSON matching this EDL schema:
{"cut_style":string,"music_track_id":string,"clips":[{"order":int,"segment_id":string,
"asset_id":string,"in_sec":number,"out_sec":number,"beat_id":string,
"transition_in":"cut|fade|dissolve","speed":number,
"title_card":{"text":string,"position":string,"style":string}|null}],"rationale":string}"""


async def editor_edl(exp, beats, segments, style, target_duration):
    seg_min = [{"segment_id": s["segment_id"], "asset_id": s["asset_id"], "in_sec": s["start_sec"],
                "out_sec": s["end_sec"], "scene_summary": s.get("scene_summary"),
                "usability_score": s.get("usability_score"), "narrative_relevance": s.get("narrative_relevance"),
                "beat_candidates": s.get("beat_candidates"), "has_people": s.get("has_people"),
                "is_duplicate_of": s.get("is_duplicate_of")} for s in segments]
    beats_min = [{"beat_id": b["beat_id"], "sequence": b["sequence"], "function": b["function"],
                  "suggested_title_card": b.get("suggested_title_card")} for b in beats]
    prompt = (f"cut_style={style}, target_duration={target_duration}.\n"
              f"Story beats (sequence order): {json.dumps(beats_min)}\n"
              f"Analyzed segments (only these are real footage): {json.dumps(seg_min)[:6000]}")
    out, meta = await _run_and_trace(exp["id"], "Editor Agent", "build_edl", EDITOR_SYS, prompt)
    return out, meta


REVISER_SYS = """You translate a creator's natural-language editing request into structured
parameters for a deterministic re-edit. Do NOT edit the video yourself.

Return ONLY valid JSON:
{"pace":"faster|slower|null","creator_presence":"less|more|null",
"duration_target":int|null,"music":"track_id|null","emphasis_beat":"beat_id|null",
"remove_segments":["segment_id"],"tone":"warmer|cooler|null"}"""


async def reviser_parse(exp_id, instruction, beats, tracks):
    prompt = (f"Instruction: {instruction!r}\n"
              f"Available music track ids: {[t['id'] for t in tracks]}\n"
              f"Beat ids: {[b['beat_id'] for b in beats]}")
    out, meta = await _run_and_trace(exp_id, "Reviser Agent", "parse_revision", REVISER_SYS, prompt, model=PROXY_FAST)
    if not isinstance(out, dict):
        out = {"pace": None, "creator_presence": None, "duration_target": None, "music": None,
               "emphasis_beat": None, "remove_segments": [], "tone": None}
    return out, meta

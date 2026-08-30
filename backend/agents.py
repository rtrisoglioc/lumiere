"""Domain agents. Each wraps the AgentBuilderAdapter and persists an AgentRun +
ToolExecution for the traceability panel. All AI outputs are bilingual (en/es).
"""
import uuid
import json

from db import db, now_iso
from agent_adapter import agent_builder

BILINGUAL = ('Every human-facing text field MUST be an object {"en": "...", "es": "..."} '
             'with natural English AND Spanish. Always include a "confidence" float 0..1. '
             'Return ONLY valid minified JSON, no markdown, no commentary.')


async def _persist_run(experience_id, agent, meta, input_summary, output, tools, evidence=None):
    run = {
        "id": str(uuid.uuid4()),
        "experience_id": experience_id,
        "agent": agent,
        "orchestration_backend": meta.get("orchestration_backend"),
        "agent_builder_connected": meta.get("agent_builder_connected"),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "latency_ms": meta.get("latency_ms"),
        "confidence": meta.get("confidence"),
        "input_summary": input_summary,
        "output": output,
        "tools": tools or [],
        "evidence": evidence or [],
        "created_at": now_iso(),
    }
    await db.agent_runs.insert_one(dict(run))
    run.pop("_id", None)
    return run


async def director_plan(experience, intent):
    system = ("You are DIRECTOR, a master film director agent inside LUMIERE. You turn a creator's raw "
              "intent about a real lived experience into a tight cinematic story plan. " + BILINGUAL)
    prompt = (
        f"Experience: title={experience['title']!r}, type={experience['type']!r}.\n"
        f"Creator intent (raw): {intent!r}.\n"
        "Produce a JSON object with keys: "
        "title (bilingual cinematic title), premise (bilingual 1-2 sentences), "
        "arc (bilingual short narrative arc), tone (bilingual), "
        "beats: array of 4-6 objects {id (slug), order (int), name (bilingual), "
        "purpose (bilingual, what this beat must accomplish), emotion (bilingual)}, "
        "confidence."
    )
    out, meta = await agent_builder.run("director", f"{experience['id']}:director", system, prompt)
    tools = [{"name": "gemini.reason", "status": "ok", "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "director", meta, f"intent: {intent[:120]}", out, tools)
    return out, meta


async def cinematographer_missions(experience, plan):
    system = ("You are CINEMATOGRAPHER, an agent that converts a story plan into concrete, prioritized shot "
              "missions the creator can actually film on a phone. " + BILINGUAL)
    prompt = (
        f"Story plan beats: {json.dumps(plan.get('beats', []))[:2500]}.\n"
        "Produce JSON: missions: array of 5-8 objects {id (slug), beat_id (matching a beat id), "
        "title (bilingual short), direction (bilingual concrete how-to-shoot instruction), "
        "shot_type (one of: wide, medium, close-up, detail, pov, establishing, action, b-roll), "
        "priority (int 1=highest..5), duration_target_sec (int 2-8)}, confidence."
    )
    out, meta = await agent_builder.run("cinematographer", f"{experience['id']}:cine", system, prompt)
    tools = [{"name": "gemini.reason", "status": "ok", "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "cinematographer", meta, "plan -> missions", out, tools)
    return out, meta


async def vision_analyze(experience, plan, mission, file_ref):
    system = ("You are VISION, a multimodal footage analyst agent. You watch real uploaded footage and judge "
              "scene content, technical usability and narrative relevance against the story plan. " + BILINGUAL)
    beats = json.dumps(plan.get("beats", []))[:1500] if plan else "[]"
    mission_txt = json.dumps(mission)[:600] if mission else "none"
    prompt = (
        "Analyze the attached footage.\n"
        f"Story beats: {beats}\nTarget mission: {mission_txt}\n"
        "Return JSON: scene (bilingual description of what happens), "
        "technical {usable (bool), quality_score (0..1), issues: array of bilingual strings}, "
        "narrative_relevance {score (0..1), matched_beats: array of beat ids, note (bilingual)}, "
        "segments: array of 1-4 {start_sec (number), end_sec (number), label (bilingual), "
        "usable (bool), quality (0..1), reason (bilingual)}, confidence. "
        "Segment times MUST be within the real clip duration."
    )
    out, meta = await agent_builder.run("vision", f"{experience['id']}:vision:{file_ref['asset_id']}", system, prompt,
                                        files=[{"path": file_ref["path"], "mime": file_ref["mime"]}])
    tools = [{"name": "gemini.multimodal", "status": "ok", "latency_ms": meta["latency_ms"],
              "input_ref": file_ref["asset_id"]}]
    evidence = []
    if isinstance(out, dict):
        seg = out.get("segments") or []
        evidence = [{"asset_id": file_ref["asset_id"], "segments": len(seg)}]
    await _persist_run(experience["id"], "vision", meta, f"analyze {file_ref['asset_id']}", out, tools, evidence)
    return out, meta


async def evaluator_assess(experience, plan, missions, analyzed):
    system = ("You are EVALUATOR (Coverage), an agent that compares the story plan against captured footage, "
              "scores story completeness with evidence and detects critical missing shots. Completeness is a "
              "decision aid, not an artistic grade. " + BILINGUAL)
    prompt = (
        f"Beats: {json.dumps(plan.get('beats', []))[:2000]}\n"
        f"Missions: {json.dumps(missions)[:1500]}\n"
        f"Analyzed footage (asset_id -> analysis summary): {json.dumps(analyzed)[:4000]}\n"
        "Return JSON: completeness {narrative (0..1), visual (0..1), emotional (0..1), overall (0..1)}, "
        "evidence: array of {dimension, ref (asset_id or beat id), note (bilingual)}, "
        "covered_beats: array of beat ids, "
        "gaps: array of {beat_id, severity ('critical'|'minor'), reason (bilingual)}, "
        "get_the_shot: array of {id (slug), for_beat (beat id), title (bilingual), "
        "direction (bilingual precise instruction), shot_type, priority (int), "
        "duration_target_sec (int), why (bilingual)}, recommendation (bilingual), confidence."
    )
    out, meta = await agent_builder.run("evaluator", f"{experience['id']}:eval", system, prompt)
    tools = [{"name": "gemini.reason", "status": "ok", "latency_ms": meta["latency_ms"]}]
    evidence = out.get("evidence", []) if isinstance(out, dict) else []
    await _persist_run(experience["id"], "evaluator", meta, "coverage assessment", out, tools, evidence)
    return out, meta


async def editor_edl(experience, plan, usable_segments):
    system = ("You are EDITOR, an agent that assembles a real cut. You output a structured EDL selecting and "
              "ordering usable segments to tell the story with good rhythm. " + BILINGUAL)
    prompt = (
        f"Beats (order matters): {json.dumps(plan.get('beats', []))[:1800]}\n"
        f"Usable segments available: {json.dumps(usable_segments)[:4000]}\n"
        "Return JSON: edl: array of {asset_id, segment_start_sec (number), segment_end_sec (number), "
        "order (int, ascending), beat_id, transition ('cut'|'fade'), note (bilingual)}, "
        "target_duration_sec (number), rationale (bilingual), confidence. "
        "Only use asset_id/segment times that exist in the provided usable segments."
    )
    out, meta = await agent_builder.run("editor", f"{experience['id']}:editor", system, prompt)
    tools = [{"name": "gemini.reason", "status": "ok", "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "editor", meta, "build EDL", out, tools)
    return out, meta


async def reviser_revise(experience, plan, current_edl, usable_segments, instruction):
    system = ("You are REVISER, an agent that edits a cut from a natural-language instruction. Produce structured "
              "EditDecisions and a NEW non-destructive EDL. If a low-confidence change alters the story meaning, "
              "set requires_confirmation true. " + BILINGUAL)
    prompt = (
        f"Creator instruction: {instruction!r}\n"
        f"Current EDL: {json.dumps(current_edl)[:3000]}\n"
        f"Usable segments available: {json.dumps(usable_segments)[:3000]}\n"
        "Return JSON: edit_decisions: array of {type ('reorder'|'trim'|'remove'|'add'|'pace'|'emphasis'), "
        "description (bilingual)}, edl: array of {asset_id, segment_start_sec, segment_end_sec, order, beat_id, "
        "transition, note (bilingual)}, requires_confirmation (bool), summary (bilingual), confidence."
    )
    out, meta = await agent_builder.run("reviser", f"{experience['id']}:reviser", system, prompt)
    tools = [{"name": "gemini.reason", "status": "ok", "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "reviser", meta, f"revise: {instruction[:120]}", out, tools)
    return out, meta

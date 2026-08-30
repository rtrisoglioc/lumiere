"""Domain agents. Each wraps the AgentBuilderAdapter (Google Gemini via Vertex AI,
or dev proxy) and persists an AgentRun with compliance trace fields (service,
operation, status, timestamp, correlation/run id). All AI outputs are bilingual.
"""
import uuid
import json

from db import db, now_iso
from agent_adapter import agent_builder, PROXY_FAST
from partner_adapter import partner

BILINGUAL = ('Every human-facing text field MUST be an object {"en": "...", "es": "..."} '
             'with natural English AND Spanish. Always include a "confidence" float 0..1. '
             'Return ONLY valid minified JSON, no markdown, no commentary.')


def _cid(correlation_id):
    return correlation_id or str(uuid.uuid4())


async def _persist_run(experience_id, agent, meta, input_summary, output, tools, evidence=None,
                       correlation_id=None, extra=None):
    run = {
        "id": str(uuid.uuid4()),
        "correlation_id": correlation_id,
        "experience_id": experience_id,
        "agent": agent,
        "service": meta.get("service"),
        "operation": meta.get("operation"),
        "status": meta.get("status", "ok"),
        "orchestration_backend": meta.get("orchestration_backend"),
        "vertex_connected": meta.get("vertex_connected"),
        "agent_builder_connected": meta.get("agent_builder_connected"),
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "latency_ms": meta.get("latency_ms"),
        "confidence": meta.get("confidence"),
        "input_summary": input_summary,
        "output": output,
        "tools": tools or [],
        "evidence": evidence or [],
        "timestamp": now_iso(),
        "created_at": now_iso(),
    }
    if extra:
        run.update(extra)
    await db.agent_runs.insert_one(dict(run))
    run.pop("_id", None)
    return run


def _context_text(context):
    if not context or not context.get("ok") or not context.get("results"):
        return None
    lines = []
    for r in context["results"][:5]:
        exc = " ".join(r.get("excerpts") or [])[:400]
        lines.append(f"- {r.get('title')}: {exc} ({r.get('url')})")
    return "\n".join(lines)


async def context_agent(experience, intent, correlation_id=None):
    """CONTEXT AGENT — calls the Parallel Search API at runtime; its result feeds
    Story Plan / Shot Missions. Runs before the Director."""
    correlation_id = _cid(correlation_id)
    objective = (f"Field-production context for a {experience.get('type')} film titled "
                 f"{experience.get('title')!r}. Intent: {intent}. Surface locations, timing, "
                 f"seasonal/lighting conditions, notable spots and logistics that improve shooting decisions.")
    queries = [
        f"{experience.get('title')} {experience.get('type')} filming locations",
        f"best time and lighting to shoot {experience.get('title')}",
        f"{intent} cinematic shooting guide",
    ]
    result = partner.search(objective, queries)
    meta = {
        "service": "parallel",
        "operation": "search",
        "status": result.get("status", "not_connected"),
        "orchestration_backend": "partner",
        "provider": "parallel",
        "model": "parallel-search",
        "latency_ms": None,
        "confidence": 0.6 if result.get("ok") else 0.0,
        "vertex_connected": None,
        "agent_builder_connected": False,
    }
    tools = [{"name": "parallel.search", "status": result.get("status"),
              "queries": result.get("queries"), "mode": result.get("mode")}]
    evidence = partner.evidence_payload(result).get("sources", [])
    await _persist_run(experience["id"], "context", meta,
                       f"parallel context: {intent[:100]}", result, tools, evidence, correlation_id)
    return result, meta


async def director_plan(experience, intent, context=None, correlation_id=None):
    correlation_id = _cid(correlation_id)
    ctx = _context_text(context)
    system = ("You are DIRECTOR, a master film director agent inside LUMIERE. You turn a creator's raw "
              "intent about a real lived experience into a tight cinematic story plan. " + BILINGUAL)
    prompt = (
        f"Experience: title={experience['title']!r}, type={experience['type']!r}.\n"
        f"Creator intent (raw): {intent!r}.\n"
        + (f"Real-world production context (from Parallel Search) — ground locations/timing/logistics in it and "
           f"reference it where relevant:\n{ctx}\n" if ctx else "")
        + "Produce a JSON object with keys: "
        "title (bilingual cinematic title), premise (bilingual 1-2 sentences), "
        "arc (bilingual short narrative arc), tone (bilingual), "
        "beats: array of 4-6 objects {id (slug), order (int), name (bilingual), "
        "purpose (bilingual, what this beat must accomplish), emotion (bilingual)}, "
        "confidence."
    )
    out, meta = await agent_builder.run("director", f"{experience['id']}:director", system, prompt,
                                        model=PROXY_FAST, operation="story_plan")
    tools = [{"name": f"{meta['service']}.reason", "status": meta["status"], "latency_ms": meta["latency_ms"]}]
    ev = [{"source": "parallel", "used_context": bool(ctx)}] if ctx else []
    await _persist_run(experience["id"], "director", meta, f"intent: {intent[:120]}", out, tools, ev, correlation_id)
    return out, meta


async def cinematographer_missions(experience, plan, context=None, correlation_id=None):
    correlation_id = _cid(correlation_id)
    ctx = _context_text(context)
    system = ("You are CINEMATOGRAPHER, an agent that converts a story plan into concrete, prioritized shot "
              "missions the creator can actually film on a phone. " + BILINGUAL)
    prompt = (
        f"Story plan beats: {json.dumps(plan.get('beats', []))[:2500]}.\n"
        + (f"Production context (Parallel Search) — tailor missions to these real conditions:\n{ctx}\n" if ctx else "")
        + "Produce JSON: missions: array of 5-8 objects {id (slug), beat_id (matching a beat id), "
        "title (bilingual short), direction (bilingual concrete how-to-shoot instruction), "
        "shot_type (one of: wide, medium, close-up, detail, pov, establishing, action, b-roll), "
        "priority (int 1=highest..5), duration_target_sec (int 2-8)}, confidence."
    )
    out, meta = await agent_builder.run("cinematographer", f"{experience['id']}:cine", system, prompt,
                                        model=PROXY_FAST, operation="shot_missions")
    tools = [{"name": f"{meta['service']}.reason", "status": meta["status"], "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "cinematographer", meta, "plan -> missions", out, tools,
                       correlation_id=correlation_id)
    return out, meta


async def vision_analyze(experience, plan, mission, file_ref, correlation_id=None):
    correlation_id = _cid(correlation_id)
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
                                        files=[{"path": file_ref["path"], "mime": file_ref["mime"]}],
                                        operation="footage_analysis")
    tools = [{"name": f"{meta['service']}.multimodal", "status": meta["status"],
              "latency_ms": meta["latency_ms"], "input_ref": file_ref["asset_id"]}]
    evidence = []
    if isinstance(out, dict):
        seg = out.get("segments") or []
        evidence = [{"asset_id": file_ref["asset_id"], "segments": len(seg)}]
    await _persist_run(experience["id"], "vision", meta, f"analyze {file_ref['asset_id']}", out, tools,
                       evidence, correlation_id)
    return out, meta


async def evaluator_assess(experience, plan, missions, analyzed, correlation_id=None):
    correlation_id = _cid(correlation_id)
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
    out, meta = await agent_builder.run("evaluator", f"{experience['id']}:eval", system, prompt,
                                        operation="coverage")
    tools = [{"name": f"{meta['service']}.reason", "status": meta["status"], "latency_ms": meta["latency_ms"]}]
    evidence = out.get("evidence", []) if isinstance(out, dict) else []
    await _persist_run(experience["id"], "evaluator", meta, "coverage assessment", out, tools,
                       evidence, correlation_id)
    return out, meta


async def editor_edl(experience, plan, usable_segments, correlation_id=None):
    correlation_id = _cid(correlation_id)
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
    out, meta = await agent_builder.run("editor", f"{experience['id']}:editor", system, prompt, operation="edl")
    tools = [{"name": f"{meta['service']}.reason", "status": meta["status"], "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "editor", meta, "build EDL", out, tools, correlation_id=correlation_id)
    return out, meta


async def reviser_revise(experience, plan, current_edl, usable_segments, instruction, correlation_id=None):
    correlation_id = _cid(correlation_id)
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
    out, meta = await agent_builder.run("reviser", f"{experience['id']}:reviser", system, prompt, operation="revise")
    tools = [{"name": f"{meta['service']}.reason", "status": meta["status"], "latency_ms": meta["latency_ms"]}]
    await _persist_run(experience["id"], "reviser", meta, f"revise: {instruction[:120]}", out, tools,
                       correlation_id=correlation_id)
    return out, meta

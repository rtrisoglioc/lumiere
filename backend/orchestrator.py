"""LUMIÈRE ORCHESTRATOR — the product's primary differentiator.

After every material production event the Orchestrator inspects the full
production state and emits an explicit, traceable DECISION (the contract from
the Media/Editing Addendum §2.1): NextAction, AgentSelected, Reason, Evidence,
Confidence, StoryCompleteness, ProductionState, UserApprovalRequired, TraceID.

Decisions are deterministic and grounded in the live state (media, analysis,
coverage, gaps, cuts, impacted versions) so Story Completeness is always
recalculated — including after deletions and substitutions (Addendum §5.1)."""
import uuid
from db import db, now_iso


def _bl(en, es):
    return {"en": en, "es": es}


async def gather_state(exp: dict) -> dict:
    exp_id = exp["id"]
    media = await db.media_assets.find({"experience_id": exp_id}, {"_id": 0}).to_list(500)
    active = [m for m in media if m.get("status") != "trashed"]
    analyzed = [m for m in active if m.get("status") == "analyzed"]
    processing = [m for m in active if m.get("status") == "processing"]
    failed = [m for m in active if m.get("status") == "failed"]
    trashed = [m for m in media if m.get("status") == "trashed"]

    cuts = await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0}).to_list(200)
    ready_cuts = [c for c in cuts if c.get("status") == "ready"]
    impacted = [c for c in cuts if c.get("impacted")]

    beats = (exp.get("plan") or {}).get("beats") or []
    beat_ids = [b.get("id") for b in beats]
    covered, usable_count = set(), 0
    for a in analyzed:
        an = a.get("analysis") or {}
        segs = [s for s in (an.get("segments") or []) if s.get("usable", True)]
        usable_count += len(segs)
        if segs:
            for bid in ((an.get("narrative_relevance") or {}).get("matched_beats") or []):
                if bid:
                    covered.add(bid)
    gap_beats = [b for b in beats if b.get("id") not in covered]
    coverage = (len(covered) / len(beat_ids)) if beat_ids else 0.0

    evaluator = exp.get("completeness") or {}
    return {
        "stage": exp.get("stage"),
        "has_plan": bool(exp.get("plan")),
        "beats_total": len(beat_ids),
        "beats_covered": len(covered),
        "coverage": round(coverage, 3),
        "gap_beats": [{"id": b.get("id"), "name": b.get("name")} for b in gap_beats],
        "media_total": len(active),
        "media_analyzed": len(analyzed),
        "media_processing": len(processing),
        "media_failed": len(failed),
        "media_trashed": len(trashed),
        "usable_segments": usable_count,
        "cuts_total": len(cuts),
        "cuts_ready": len(ready_cuts),
        "impacted_cuts": [{"id": c["id"], "version": c.get("version")} for c in impacted],
        "latest_cut": (sorted(cuts, key=lambda c: c.get("version", 0))[-1] if cuts else None),
        "evaluator_overall": (evaluator.get("completeness") or {}).get("overall") if evaluator else None,
    }


def decide(exp: dict, st: dict, trace_id: str) -> dict:
    """Deterministic next-best-action grounded in the live production state."""
    completeness = st["coverage"]
    conf = 0.5
    approval = False

    if not st["has_plan"]:
        action, agent = "create_plan", "director"
        reason = _bl("No story plan yet. Capture your intent so I can direct the shoot.",
                     "Aún no hay plan de historia. Cuéntame tu intención para dirigir el rodaje.")
        required = _bl("Your creative intent", "Tu intención creativa")
        conf = 0.9
    elif st["media_total"] == 0:
        action, agent = "capture", "cinematographer"
        reason = _bl("The plan is ready. Film the shot missions to give me footage to work with.",
                     "El plan está listo. Graba las misiones de toma para darme material.")
        required = _bl("Upload footage for the missions", "Sube material de las misiones")
        conf = 0.85
    elif st["media_processing"] > 0:
        action, agent = "wait_analysis", "vision"
        reason = _bl(f"Analyzing {st['media_processing']} clip(s) with multimodal Vision.",
                     f"Analizando {st['media_processing']} clip(s) con Visión multimodal.")
        required = _bl("Nothing — analysis in progress", "Nada — análisis en curso")
        conf = 0.7
    elif st["impacted_cuts"]:
        action, agent = "recover_impacted", "orchestrator"
        reason = _bl("A cut lost source media it depended on. Restore the clip or re-render from what remains.",
                     "Un corte perdió media de la que dependía. Restaura el clip o re-renderiza con lo que queda.")
        required = _bl("Restore the deleted clip or approve a re-render",
                       "Restaura el clip borrado o aprueba un re-render")
        approval = True
        conf = 0.8
    elif st["media_analyzed"] > 0 and st["evaluator_overall"] is None:
        action, agent = "evaluate", "evaluator"
        reason = _bl("Footage is analyzed. Let me score story completeness and detect any missing shots.",
                     "El material está analizado. Déjame puntuar la completitud y detectar tomas faltantes.")
        required = _bl("Run coverage evaluation", "Ejecutar evaluación de cobertura")
        conf = 0.85
    elif st["gap_beats"] and completeness < 0.75:
        action, agent = "get_the_shot", "evaluator"
        names = ", ".join([(g["name"] or {}).get("en", g["id"]) for g in st["gap_beats"][:3]])
        reason = _bl(f"Your story is almost there. One more shot for: {names} will strengthen it.",
                     f"Tu historia casi está. Una toma más para: {names} la reforzará.")
        required = _bl("Capture the recommended missing shot(s)", "Captura la(s) toma(s) faltante(s)")
        conf = 0.8
    elif st["usable_segments"] > 0 and st["cuts_total"] == 0:
        action, agent = "create_cut", "editor"
        reason = _bl("Enough strong material exists. I'll assemble a real first cut.",
                     "Hay suficiente material fuerte. Voy a montar un primer corte real.")
        required = _bl("Create the first cut", "Crear el primer corte")
        conf = 0.85
    elif st["cuts_ready"] > 0 and completeness >= 0.75:
        action, agent = "deliver", "orchestrator"
        reason = _bl("Your story is complete and a cut is ready. Refine it or deliver the final film.",
                     "Tu historia está completa y hay un corte listo. Refínalo o entrega la película final.")
        required = _bl("Deliver or keep refining", "Entregar o seguir refinando")
        conf = 0.9
    else:
        action, agent = "refine", "reviser"
        reason = _bl("You can keep refining the cut conversationally or capture more footage.",
                     "Puedes seguir refinando el corte conversando o capturar más material.")
        required = _bl("Refine or add footage", "Refina o agrega material")
        conf = 0.7

    evidence = [
        {"metric": "coverage", "value": st["coverage"], "note": _bl(
            f"{st['beats_covered']}/{st['beats_total']} beats covered",
            f"{st['beats_covered']}/{st['beats_total']} beats cubiertos")},
        {"metric": "usable_segments", "value": st["usable_segments"]},
        {"metric": "media", "value": st["media_analyzed"], "note": _bl(
            f"{st['media_analyzed']} analyzed, {st['media_trashed']} in trash",
            f"{st['media_analyzed']} analizados, {st['media_trashed']} en papelera")},
    ]
    if st["impacted_cuts"]:
        evidence.append({"metric": "impacted_cuts", "value": len(st["impacted_cuts"]),
                         "refs": [c["id"] for c in st["impacted_cuts"]]})

    return {
        "id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "experience_id": exp["id"],
        "next_action": action,
        "agent_selected": agent,
        "reason": reason,
        "required_input": required,
        "evidence": evidence,
        "confidence": conf,
        "story_completeness": round(completeness, 3),
        "production_state": st,
        "user_approval_required": approval,
        "created_at": now_iso(),
    }


async def orchestrate(exp: dict, trace_id: str = None) -> dict:
    """Gather live state, decide, and persist the decision (traceable)."""
    trace_id = trace_id or exp.get("correlation_id") or str(uuid.uuid4())
    st = await gather_state(exp)
    decision = decide(exp, st, trace_id)
    await db.orchestrator_decisions.insert_one(dict(decision))
    decision.pop("_id", None)
    # Mirror into agent_runs so it appears in the compliance Trace.
    await db.agent_runs.insert_one({
        "id": str(uuid.uuid4()), "correlation_id": trace_id, "experience_id": exp["id"],
        "agent": "orchestrator", "service": "orchestrator", "operation": "decide",
        "status": "ok", "provider": "lumiere", "model": "orchestrator-v1",
        "confidence": decision["confidence"], "latency_ms": 0,
        "input_summary": f"decide -> {decision['next_action']}",
        "output": {"next_action": decision["next_action"], "reason": decision["reason"]},
        "tools": [{"name": "orchestrator.decide", "next_action": decision["next_action"],
                   "agent_selected": decision["agent_selected"]}],
        "evidence": decision["evidence"], "timestamp": now_iso(), "created_at": now_iso(),
    })
    # Persist live completeness on the experience (deletion-aware).
    await db.experiences.update_one({"id": exp["id"]}, {"$set": {
        "live_completeness": decision["story_completeness"],
        "orchestrator_decision": {k: decision[k] for k in
                                  ("next_action", "agent_selected", "reason", "required_input",
                                   "confidence", "story_completeness", "user_approval_required", "trace_id")}}})
    return decision


async def recompute_cut_impact(exp_id: str) -> list:
    """Recompute the impacted flag for EVERY CutVersion from the CURRENT asset
    availability (Addendum §4.4). A cut is impacted iff its EDL references an
    asset that is now missing or trashed. Clears the flag when all clips are
    available again (so a restore un-sticks the orchestrator loop)."""
    assets = await db.media_assets.find(
        {"experience_id": exp_id}, {"_id": 0, "id": 1, "status": 1}).to_list(500)
    available = {a["id"] for a in assets if a.get("status") != "trashed"}
    cuts = await db.cut_versions.find({"experience_id": exp_id}, {"_id": 0}).to_list(200)
    impacted = []
    for c in cuts:
        refs = [clip.get("asset_id") for clip in (c.get("edl") or [])]
        missing = [r for r in refs if r and r not in available]
        if missing:
            impacted.append(c["id"])
            await db.cut_versions.update_one({"id": c["id"]}, {"$set": {
                "impacted": True,
                "impact_reason": _bl("A source clip used in this cut was deleted.",
                                     "Un clip fuente usado en este corte fue borrado.")}})
        elif c.get("impacted"):
            await db.cut_versions.update_one(
                {"id": c["id"]}, {"$set": {"impacted": False}, "$unset": {"impact_reason": ""}})
    return impacted


async def mark_impacted_cuts(exp_id: str, asset_id: str) -> list:
    """Back-compat shim → full recompute (also clears stale flags)."""
    return await recompute_cut_impact(exp_id)

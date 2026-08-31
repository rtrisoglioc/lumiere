"""LUMIÈRE ADK sub-agents (deployed to Vertex AI Agent Engine / Agent Runtime).

Self-contained package: reasoning runs on Google Gemini via Vertex AI (ADK).
No other AI providers. The Context sub-agent calls the Parallel Search API at
runtime (Partner track) as an ADK tool. Vision consumes footage via a GCS
`gs://` URI (Vertex multimodal), keeping Google Cloud provenance.
"""
import os
import json
import requests

from google.adk.agents import LlmAgent

TEXT_MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-pro"

BILINGUAL = ('Every human-facing text field MUST be an object {"en":"...","es":"..."} with natural '
             'English AND Spanish. Always include a "confidence" float 0..1. Return ONLY valid minified JSON.')


# ---- Partner (Parallel) tool used by the Context sub-agent at runtime ----
def parallel_search(objective: str, queries: list) -> dict:
    """Call the Parallel Search API (Partner track). Returns real web context that
    must influence the Story Plan / Shot Missions. Requires PARALLEL_API_KEY."""
    key = (os.environ.get("PARALLEL_API_KEY") or "").strip()
    if not key:
        return {"connected": False, "status": "not_connected", "results": []}
    try:
        resp = requests.post(
            "https://api.parallel.ai/v1/search",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={"objective": objective, "search_queries": queries[:5],
                  "mode": os.environ.get("PARALLEL_MODE") or "basic", "max_chars_total": 40000},
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [{"title": r.get("title"), "url": r.get("url"),
                    "excerpts": [str(e)[:600] for e in (r.get("excerpts") or [])][:3]}
                   for r in (data.get("results") or [])[:8]]
        return {"connected": True, "status": "ok", "objective": objective, "results": results}
    except requests.HTTPError as e:
        body = ""
        try:
            body = e.response.text[:300]
        except Exception:
            pass
        return {"connected": True, "status": "error", "error": f"{str(e)[:200]} :: {body}", "results": []}
    except Exception as e:
        return {"connected": True, "status": "error", "error": str(e)[:300], "results": []}


context_agent = LlmAgent(
    name="context",
    model=TEXT_MODEL,
    description="Retrieves real-world production context via the Parallel Search API.",
    instruction=("You are CONTEXT. Given the creator's intent and experience, call the parallel_search tool to "
                 "gather real locations, timing, seasonal/lighting conditions and logistics. Summarize the "
                 "evidence into a compact context brief that later agents must use. " + BILINGUAL),
    tools=[parallel_search],
)

director_agent = LlmAgent(
    name="director",
    model=TEXT_MODEL,
    description="Turns intent + context into a tight cinematic story plan.",
    instruction=("You are DIRECTOR. Using the context brief, produce JSON: title, premise, arc, tone (all bilingual), "
                 "beats: 4-6 {id, order, name, purpose, emotion}, confidence. Ground locations/timing in the "
                 "provided context where relevant. " + BILINGUAL),
)

cinematographer_agent = LlmAgent(
    name="cinematographer",
    model=TEXT_MODEL,
    description="Converts the story plan into prioritized, filmable shot missions.",
    instruction=("You are CINEMATOGRAPHER. Produce JSON: missions: 5-8 {id, beat_id, title, direction, shot_type "
                 "(wide|medium|close-up|detail|pov|establishing|action|b-roll), priority(1..5), "
                 "duration_target_sec(2..8)}, confidence. Tailor to the real context. " + BILINGUAL),
)

vision_agent = LlmAgent(
    name="vision",
    model=VISION_MODEL,
    description="Multimodal footage analyst; reads footage from a gs:// URI.",
    instruction=("You are VISION. Analyze the provided footage (a gs:// URI is supplied). Return JSON: scene, "
                 "technical{usable,quality_score,issues[]}, narrative_relevance{score,matched_beats[],note}, "
                 "segments: 1-4 {start_sec,end_sec,label,usable,quality,reason}, confidence. " + BILINGUAL),
)

evaluator_agent = LlmAgent(
    name="evaluator",
    model=TEXT_MODEL,
    description="Scores story completeness and detects missing shots.",
    instruction=("You are EVALUATOR. Return JSON: completeness{narrative,visual,emotional,overall}, evidence[], "
                 "covered_beats[], gaps[{beat_id,severity,reason}], get_the_shot[{id,for_beat,title,direction,"
                 "shot_type,priority,duration_target_sec,why}], recommendation, confidence. " + BILINGUAL),
)

editor_agent = LlmAgent(
    name="editor",
    model=TEXT_MODEL,
    description="Assembles a structured EDL from usable segments.",
    instruction=("You are EDITOR. Return JSON: edl:[{asset_id,segment_start_sec,segment_end_sec,order,beat_id,"
                 "transition(cut|fade),note}], target_duration_sec, rationale, confidence. Only use provided "
                 "segments. " + BILINGUAL),
)

reviser_agent = LlmAgent(
    name="reviser",
    model=TEXT_MODEL,
    description="Applies a natural-language edit into a new non-destructive EDL.",
    instruction=("You are REVISER. Return JSON: edit_decisions[{type,description}], edl[...], "
                 "requires_confirmation(bool), summary, confidence. " + BILINGUAL),
)

ALL_SUBAGENTS = [context_agent, director_agent, cinematographer_agent, vision_agent,
                 evaluator_agent, editor_agent, reviser_agent]

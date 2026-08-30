"""LUMIÈRE root ADK orchestrator, deployed to Vertex AI Agent Engine.

One reasoningEngine hosts this root agent and internally coordinates the seven
sub-agents. FastAPI (external gateway) invokes this deployment per pipeline stage
via agent_engines.get(RESOURCE).query / async_stream_query, passing a JSON
message {operation, system, payload}. Reasoning is Google Gemini via Vertex AI.
"""
from google.adk.agents import LlmAgent

from .subagents import ALL_SUBAGENTS

ROOT_MODEL = "gemini-2.5-flash"

root_agent = LlmAgent(
    name="lumiere_orchestrator",
    model=ROOT_MODEL,
    description="Orchestrates the LUMIÈRE agentic production crew (pre-production, capture direction, "
                "footage understanding, gap detection, post-production).",
    instruction=(
        "You are the LUMIÈRE orchestrator, an agentic media & entertainment production crew.\n"
        "Each request is a JSON message with keys: operation, system, payload.\n"
        "Route to the correct sub-agent by operation:\n"
        " - 'context'        -> context (call parallel_search; context must influence later stages)\n"
        " - 'story_plan'     -> director\n"
        " - 'shot_missions'  -> cinematographer\n"
        " - 'footage_analysis' -> vision (payload.gcs_uri points to the footage)\n"
        " - 'coverage'       -> evaluator\n"
        " - 'edl'            -> editor\n"
        " - 'revise'         -> reviser\n"
        "Honor the sub-agent's system guidance and return ONLY the sub-agent's JSON result. "
        "Never claim media was generated. LUMIÈRE acts before, during and after capture."
    ),
    sub_agents=ALL_SUBAGENTS,
)

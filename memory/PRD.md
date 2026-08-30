# LUMIÈRE — Agentic Experience Studio (PRD)

## Original problem statement
LUMIÈRE turns real lived experiences into cinema through an agentic closed loop. Bilingual ES/EN, mobile-first PWA. Frase eje: "You live it. LUMIÈRE directs it." The wow: the AI understands the story you want, analyzes your footage, detects what's missing, sends you to capture it, and rebuilds the film with the new material. No simulated core capabilities.

## User decisions (confirmed)
1. Agentic orchestration: AgentBuilderAdapter interface ready but Google Agent Builder NOT connected (awaiting GCP creds). Reasoning runs on REAL Gemini via Emergent Universal Key. `orchestration_backend="direct_gemini"`.
2. Media storage: Emergent object storage (originals preserved, checksum, versioned derivatives).
3. Identity: Emergent-managed Google Auth.
4. Partner track: NOT selected → PartnerAdapter is an explicit MOCK (health_check/execute_workflow_capability/evidence_payload/error_mapping).
5. Scope: full vertical loop, functional over broad.

## Architecture
- Frontend: React + Tailwind (craco), i18n ES/EN, cinematic dark theme (Playfair/Manrope/JetBrains Mono). PWA manifest.
- Backend: FastAPI, all routes under /api. Modular: db.py, storage.py, auth.py, agent_adapter.py (AgentBuilderAdapter), partner_adapter.py (PartnerAdapter mock), ffmpeg_worker.py, agents.py, server.py.
- AI: emergentintegrations LlmChat, model gemini-3.1-pro-preview (multimodal video + reasoning). Every agent turn persists an AgentRun + ToolExecution (latency, confidence, evidence).
- Media: FFmpeg real render from structured EDL; non-destructive versioned cuts.
- DB: MongoDB (users, user_sessions, experiences, media_assets, cut_versions, agent_runs). UUID ids, `{"_id":0}` projection.

## Personas
- The Creator: converts travel/event/lifestyle experiences into cinematic content without carrying full production overhead.

## Core requirements (static)
- Closed loop: Intent → Plan → Direct → Capture/Upload → Understand → Evaluate → Detect Gap → GET THE SHOT → Re-analyze → Real FFmpeg Edit → Conversational Re-edit → Final Film.
- Originals never destroyed; edits reversible/versioned. Private by default. Full agent traceability.

## Implemented (2026-06)
- Emergent Google Auth (cookie + Bearer fallback), protected routes, AuthCallback race-safe.
- Create Experience + Dashboard.
- Director + Cinematographer → bilingual Story Plan (title/premise/arc/tone/beats) + prioritized Shot Missions. (~45s latency)
- Real footage upload → object storage (checksum) → background Vision multimodal analysis (scene, technical usability, narrative relevance, usable segments).
- Evaluator → Story Completeness (narrative/visual/emotional/overall + evidence), Detected Gaps, GET THE SHOT missions.
- Editor → EDL → real FFmpeg rendered CutVersion (validated: 5-clip cut rendered).
- Reviser → conversational re-edit ("make it faster") → new non-destructive CutVersion (validated: 9.6s → 5.6s).
- Agent Traceability panel (7 runs w/ latency+confidence), Adapter status (Agent Builder NOT CONNECTED, Partner MOCK).
- Bilingual UI toggle EN/ES. Verified end-to-end (backend via curl, frontend via testing agent 100%).

## Backlog / remaining (P1)
- P1: Connect Google Cloud Agent Builder / Vertex Agent Engine (swap AgentBuilderAdapter.run body) — needs GCP project + service account.
- P1: Select + implement partner track (IBM/Grafana/Parallel/ClickHouse/Replit) real integration behind PartnerAdapter.
- P1: Planning latency optimization (<30s target; currently ~45s — consider a flash model for Director/Cinematographer).
- P2: Brand DNA, Creator×Brand Match, Cut B/C, resumable upload after app close, provenance export, image (non-video) analysis polish.

## Next tasks
- Optimize planning latency; add DialogDescription a11y (done); wire Agent Builder + partner when creds/track available.

## Refinement — UX/Monetization layer (2026-06, additive, P0 untouched)
- Dual light/dark cinematic-editorial system from Master Spec (Cinema Ivory/Warm White/Lumière Ink/Golden Hour/Sage/Iris AI). Light: Landing, Home, Account, Pricing, Create Video. Dark: Experience workspace (re-skinned), Trace.
- New screens: Home (/studio, replaces dashboard — welcome, active experience + continue, create new, recent grid, plan+usage), Account (/account — profile, plan, usage, settings, privacy, sign out; ZERO video players), Pricing (/pricing — 3 tiers FREE/CREATOR(recommended)/PRO, monthly/yearly, plan switch, FAQ), Create Video (/create-video — AI video gen UI).
- Header with avatar dropdown + nav; LoopStrip signature marquee; positioning line "Other AI tools edit what you captured. LUMIÈRE helps you understand what to capture next."
- Backend additive: plans.py (configurable placeholder plans/limits), /account, /pricing/plans, /account/plan, usage computation; music.py (4 CC0 royalty-free tracks synthesized via FFmpeg, seeded to object storage); stock music scoring muxed into real cuts (optional music_id on cut/revise).
- VertexVideoAdapter (Vertex AI Veo) = intentional MOCK ('not_connected') per user; interface ready for GCP. video_jobs persisted; UI shows pending state honestly.
- Verified: testing agent iteration 2 = 100% (new layer + P0 regression + real music mux V3 in ~24s; Account has 0 video players).

## Remaining (P1)
- Connect Vertex AI (Veo) for real video generation/enhancement (swap VertexVideoAdapter body) — needs GCP creds.
- Connect Google Agent Builder + select partner track; real payment processing for Pricing.
- Planning latency <30s.

## Hackathon Compliance — Phase A (2026-06, additive, P0 preserved)
- Secrets/repo hygiene: `.gitignore` now excludes all `.env`; added `backend/.env.example`, `frontend/.env.example`, root `LICENSE` (MIT), `README.md`. No secrets in `.py`. `EMERGENT_LLM_KEY` kept only in git-ignored `.env` (dev + object-storage init).
- Compliance Trace: every AgentRun now records `service`, `operation`, `status`, `timestamp`, `correlation_id`; Trace UI shows Google Cloud (Vertex/Agent Builder) + Partner (Parallel) participation and per-run svc/op/status/run-id.
- Production adapters (activate automatically when secrets exist, else graceful not_connected): `vertex_gemini_adapter.py` (Gemini via Vertex AI, google-genai, lazy import), `agent_adapter.py` real routing (vertex-agent-engine → vertex-ai → emergent-proxy dev fallback), `partner_adapter.py` = ParallelPartnerAdapter (real POST /v1/search, x-api-key).
- Context Agent added BEFORE Story Plan: calls Parallel Search at runtime; its context is passed into Director + Cinematographer prompts (materially influences plan/missions when connected). Shared correlation_id across context→director→cinematographer.
- Planning latency reduced to ~24s (<30s) using gemini flash for planning agents.
- Env vars introduced: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_APPLICATION_CREDENTIALS_JSON, VERTEX_AGENT_ENGINE_ID, PARALLEL_API_KEY.
- Still not connected (awaiting secrets): Vertex/Agent Builder (GOOGLE_APPLICATION_CREDENTIALS_JSON), Parallel (PARALLEL_API_KEY). Veo remains optional/mock. No prohibited AI providers present.

## Phase B-1 (2026-06) — ADK package + deploy prep (NOT deployed)
- Created `backend/adk_app/` (isolated from serving runtime): `agent.py` root `lumiere_orchestrator`, `subagents.py` (Context+Parallel tool, Director, Cinematographer, Vision[gs:// multimodal], Evaluator, Editor, Reviser), `__init__.py`, `requirements-deploy.txt` (google-adk 2.8.0, aiplatform[adk,agent_engines] 1.148.1, google-genai 2.20.0).
- `backend/deploy_agent_engine.py`: one-off `agent_engines.create(AdkApp(root, enable_tracing=True))` → creates ONE reasoningEngine; guarded (exits if no creds); prints REASONING_ENGINE_NAME for VERTEX_AGENT_ENGINE_ID.
- `backend/gcs_media.py`: GCS upload → gs:// URI bridge for Vision path (lazy import, graceful not_configured).
- Env vars added (empty placeholders): GCS_BUCKET, GCS_STAGING_BUCKET, PARALLEL_MODE.
- Nothing deployed. Golden path verified intact (existing exp: 2 media, 3 cuts). adk_app not imported by runtime; google-adk NOT installed in serving env (deploy-time only).

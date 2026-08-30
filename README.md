# LUMIÈRE — Agentic Experience Studio

**You live it. LUMIÈRE directs it.** An agentic media & entertainment production crew for solo filmmakers and small crews. LUMIÈRE acts **before, during and after** capture: it plans the story, directs field capture, understands footage, detects narrative gaps, tells you the next shot to get, and assembles a real edit — not just post-processing footage you already have.

> Hackathon: **Agentic Cinema — Google Cloud Partnerships**. Partner track: **Parallel**.

## Architecture

```
Experience Intent
  → Context Agent  ── Parallel Search API (runtime) ──┐
  → Story Plan (Director)      Gemini + Agent Builder │ context materially
  → Shot Missions (Cinematographer)                    │ influences plan/missions
  → Capture / Upload (real user media)
  → Understand (Vision, Gemini multimodal)
  → Story Completeness + Gap detection (Evaluator)
  → GET THE SHOT (context-aware) → capture again → re-evaluate
  → Edit (deterministic FFmpeg render) → Conversational re-edit (Reviser)
  → Final film + Trace (Google Cloud + Partner runtime evidence)
```

- **AI reasoning/multimodal:** Google **Gemini** via **Vertex AI** (Google Gen AI SDK). Orchestrated through the `AgentBuilderAdapter` (Vertex Agent Engine when an engine id is configured).
- **Partner (runtime):** **Parallel Search API** (`POST https://api.parallel.ai/v1/search`) called by the Context Agent; results influence Story Plan / Shot Missions.
- **Deterministic media:** **FFmpeg** for real, non-destructive, versioned cut rendering (non-AI tooling).
- **Storage/Auth/Host:** Emergent object storage (non-AI), Emergent-managed Google login, Emergent hosting.
- **No prohibited AI at runtime:** no OpenAI, Anthropic, AWS/Microsoft AI, or fal.ai. Gemini (Google) + Parallel built-in capabilities only.

## Prerequisites
- Python 3.11+, Node 18+/Yarn, MongoDB, FFmpeg.
- A Google Cloud project with **Vertex AI API** enabled and a least-privilege service account (`roles/aiplatform.user`).
- A Parallel API key (Search API).

## Environment variables
Backend (`backend/.env`, injected as secrets at deploy — never committed):

| Variable | Purpose |
| --- | --- |
| `MONGO_URL`, `DB_NAME` | MongoDB connection |
| `GOOGLE_CLOUD_PROJECT` | `lumiere-agentic-cinema` |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full service-account JSON (multi-line), via secret manager |
| `VERTEX_AGENT_ENGINE_ID` | Optional Vertex Agent Engine resource id/name |
| `PARALLEL_API_KEY` | Parallel Search API key |
| `EMERGENT_LLM_KEY` | Dev-only fallback reasoning + object storage init |

See `backend/.env.example` and `frontend/.env.example`. **Secrets are never committed** (`.gitignore` excludes all `.env`).

## Google Cloud setup
```bash
gcloud config set project lumiere-agentic-cinema
gcloud services enable aiplatform.googleapis.com
# least-privilege runtime SA already provisioned:
#   lumiere-agent-runtime@lumiere-agentic-cinema.iam.gserviceaccount.com  (roles/aiplatform.user)
```
Provide the service-account JSON to the deploy platform's secret manager as `GOOGLE_APPLICATION_CREDENTIALS_JSON` (do not create/commit a key file in the repo).

## Partner setup (Parallel)
Set `PARALLEL_API_KEY` as a secret. The Context Agent calls `POST /v1/search` with header `x-api-key`. Until the key is set, the adapter reports `not_connected` and the pipeline degrades gracefully without fabricating partner data.

## Local run
```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
# frontend
cd frontend && yarn install && yarn start
```
Health checks: `GET /api/agent/health`, `GET /api/partner/health`.

## Deployment
Deploy on Emergent. Set production secrets in **Manage Publishes → Secrets** (KMS-encrypted, runtime-injected). Redeploy to apply.

## Demo path
Create Experience → (Context Agent / Parallel) → Story Plan → Shot Missions → Upload → Gemini analysis → Completeness → GET THE SHOT → re-upload → re-evaluate → FFmpeg cut → conversational re-edit → final film → Trace.

## Limitations / current state
- Vertex Gemini + Agent Builder and Parallel adapters are **production-ready but disconnected** until the corresponding secrets are set (then they activate with no code change). In dev without GCP/Parallel secrets, reasoning runs via the Emergent Gemini proxy and Partner is `not_connected`.
- Veo / Vertex video generation is **optional and not claimed as real** until Vertex credentials are connected and tested.

## License
MIT — see [LICENSE](./LICENSE).

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

## Phase B-2 code (2026-06) — Option A gateway (NOT deployed)
- `gateway/` (Cloud Run service, keyless ADC): `server.py` (FastAPI: /healthz, /agent→agent_engines.get(ENGINE).query, /vision→GCS upload+query with gs:// URI, bearer LUMIERE_GATEWAY_TOKEN), `Dockerfile`, `requirements.txt`, `.dockerignore`.
- `backend/agent_adapter.py`: gateway-first routing — if LUMIERE_GATEWAY_URL set → call Cloud Run gateway over HTTPS (service=vertex-agent-engine); else vertex direct; else emergent-proxy (DEV). `_gateway()` handles /agent and /vision(multipart).
- `backend/deploy_agent_engine.py`: keyless ADC primary (optional JSON), passes env_vars (PARALLEL_API_KEY, GCS_BUCKET, project/location) into agent_engines.create.
- Env placeholders added: LUMIERE_GATEWAY_URL, LUMIERE_GATEWAY_TOKEN (token generated in git-ignored backend/.env).
- No JSON key, no policy change. Golden path (DEV) re-verified working after edits.

---

## CHANGELOG — 2026-06 (Fork: Redesign + Admin + Veo + Social Studio)

### Phase A (paused, code-ready): Parallel Context via Agent Engine
- `agents.py::context_agent` now routes `operation="context"` through the Cloud Run gateway when enabled → the ADK `parallel_search` tool runs INSIDE the Agent Engine (uses engine's own PARALLEL_API_KEY). Trace: service=vertex-agent-engine, operation=context.
- Root cause fixed: Parallel mode `"base"` was invalid (422) → changed to `"basic"` in `.env`, `partner_adapter.py`, `adk_app/subagents.py`.
- `deploy_agent_engine.py` now updates in-place (same engine ID) when `VERTEX_AGENT_ENGINE_ID` is set, and always passes a valid PARALLEL_MODE.
- STATUS: backend validated (routing/trace OK); returns real sources only AFTER user redeploys the engine with PARALLEL_MODE=basic. PENDING USER REDEPLOY.

### Phase 1 — Full site redesign (DONE, tested)
- New public landing `pages/Landing.jsx` matching reference image, keeping exact palette/fonts. Sections: hero, LoopStrip, Narrative Gap, Capture→Cinema, Crew, dark Detect-Gap band, Speak Cinema, pricing, FAQ, final CTA, footer. Bilingual ES/EN. Route `/` = Landing; `/login` kept.

### Phase 2 — Admin profile + panel (DONE, tested)
- `auth.py`: admin role from env `ADMIN_EMAILS` (currently admin@getlumiere.ai); `require_admin` dependency; `get_current_user` adds `is_admin`.
- `admin.py` router `/api/admin/*`: overview metrics, plans GET/PUT (prices/quotas/entitlements editable at runtime), users list + change plan, video-jobs & social-posts monitors, settings.
- `plans_store.py`: DB-backed plan overrides (site_config) with plans.py fallback. `/account`, `/pricing/plans`, `/account/plan` now async DB-backed.
- Frontend `pages/Admin.jsx` (admin-only, redirects non-admins): tabs overview/plans/users/video/social; editable plan fields + Save.

### Phase 3 — AI Video Generation via Vertex Veo (DONE backend/UI; NEEDS GATEWAY REDEPLOY)
- Gateway `gateway/server.py`: added `/video` (submit, returns operation_name), `/video/status` (poll), `/video/download` (stream mp4 from GCS); renamed `/healthz`→`/status`. Uses google-genai + ADC. Added google-genai to gateway/requirements.txt (aiplatform preserved).
- `vertex_video_adapter.py`: submit/poll/download via gateway (no mock).
- `server.py /api/video/generate`: BACKEND-enforced gating — Free=403 video_not_entitled, quota (limits.ai_generations/month)=403 quota_exceeded; then submits to gateway. `/api/video/jobs` polls & updates RUNNING jobs; `/api/video/{id}/download` proxies stream.
- Frontend `pages/CreateVideo.jsx`: prompt/aspect/duration, quota meter, jobs grid with polling + player; Free sees locked upsell.
- BLOCKER: gateway `/video` not deployed yet → generation fails at gateway step until user redeploys gateway (Cloud Run) with the new `lumiere_deploy.zip` (apply gateway/server.py AND gateway/requirements.txt — google-genai added, aiplatform 1.165.1 preserved). Config: env `VEO_MODEL` default veo-3.1-lite-generate-001.
- 2026-06 FIX: default model veo-3.0-generate-001 did NOT exist (404) → changed default to `veo-3.1-lite-generate-001` (available: veo-3.1-generate-001 / -lite- / -fast-). Fixed stuck-GENERATING bug: gateway `/video/status` was calling google-genai `operations.get(name_string)` → `'str' has no attribute 'name'` (needs an Operation OBJECT). Rewrote status to detect completion by the mp4 landing in GCS under the output prefix (google-cloud-storage list_blobs, 100% reliable) + best-effort operation object for failures. Backend now stores `output_prefix` and passes it to poll. NEEDS one more gateway redeploy (apply gateway/server.py).

### Phase 4 — AI Social Content Studio (DONE, tested, Studio-exclusive)
- `social.py` router `/api/social/*` (entitlement `social` enforced): POST /plan (Universal Key gemini text → bilingual content plan + post drafts: caption, hashtags, network, design_prompt); POST /posts/{id}/design (Nano Banana image → object storage); GET /posts/{id}/image; PUT /posts/{id}; POST /posts/{id}/schedule (network + date/time); POST /posts/{id}/publish (SIMULATED); DELETE.
- Frontend `pages/SocialStudio.jsx`: brief→plan, post cards with AI design, network selector, datetime schedule, simulated publish. Free/Creator see locked upsell.
- Social models env-configurable: SOCIAL_TEXT_MODEL / SOCIAL_IMAGE_MODEL.

### Plans (defaults, admin-editable)
- Free $0: no video, no social. Creator $49: video ON, 20 clips/mo. Studio $149: video expanded (100), Social Studio ON.

### Testing: iteration_7.json → backend 20/20, frontend 23/23, no issues.

### MOCKED / PENDING
- Social publishing to real networks = SIMULATED (status flip only).
- Veo video generation = blocked until gateway redeploy.
- Parallel context real sources = blocked until Agent Engine redeploy (PARALLEL_MODE=basic).
- No real payments (plan changes are placeholders).


---

## ADDENDUM v1.0 — Orchestrator, Media Control & Editing (DONE, tested — iteration_8.json 13/13 backend, 7/7 frontend)

**THE product differentiator.** After every material event the Orchestrator emits an explicit, traceable DECISION.

### orchestrator.py (new)
- `gather_state(exp)`: live production state (media active/analyzed/processing/trashed, beats coverage, usable segments, cuts, impacted cuts).
- `decide(exp, st, trace_id)`: deterministic next-best-action → contract {next_action, agent_selected, reason(bilingual), required_input, evidence[], confidence, story_completeness, production_state, user_approval_required, trace_id}. Actions: create_plan → capture → wait_analysis → evaluate → get_the_shot → create_cut → recover_impacted → deliver → refine.
- `orchestrate(exp)`: persists decision to `orchestrator_decisions`, mirrors into `agent_runs` (agent=orchestrator, operation=decide) for the Trace, and stores `live_completeness`/`orchestrator_decision` on the experience. Deletion-aware (recomputed every call).
- `recompute_cut_impact(exp_id)`: sets/clears `impacted` on every CutVersion from current asset availability (missing/trashed EDL refs). Un-sticks the loop on restore.

### server.py endpoints (new)
- GET /experiences/{id}/orchestrator (recompute+return); GET /experiences/{id}/decisions.
- Media deletion (§3): GET /media/{id}/impact (cuts + beats_at_risk + bilingual msg); DELETE /media/{id} (soft Trash default; `?permanent=true&confirm=true` hard; `&force=true` required if used in a cut → no silent broken renders); POST /media/{id}/restore (clears impacted).
- DELETE /cuts/{id} (render only, originals preserved); GET /experiences/{id}/impact; DELETE /experiences/{id} (soft trash / permanent+confirm).
- Editing (§4): POST /cuts/{id}/remove-clip {asset_id} → NEW CutVersion (parent_id, kind=edit) without deleting original; re-render. Conversational /cuts/{id}/revise already existed (EDIT-02).
- list_experiences excludes trashed; usable/analyzed pools exclude trashed (status-based). deletion_events collection logs all deletions (no media bytes retained). AI never auto-permanent-deletes.

### Frontend
- `components/OrchestratorPanel.jsx`: "LUMIÈRE DIRECTS" banner — reason, required input, completeness bar, evidence chips, primary CTA that routes to the right tab; "Your call" badge when user_approval_required. Integrated at top of Experience `<main>`.
- `components/MediaActions.jsx`: per-media Trash / Restore / Delete-permanently with impact dialog (bilingual), 2nd confirm for permanent, 409 force-delete handling for in-use clips.

### PENDING from prior turns (unchanged)
- Veo video generation: needs ONE gateway redeploy (fix for stuck-GENERATING: /video/status now GCS-list based; default model veo-3.1-lite-generate-001). NOT tested here per instruction.
- Long video (Cinematic Sequence, multi-clip FFmpeg stitch): awaiting user's duration-cap choice.
- Parallel context real sources: awaiting Agent Engine redeploy (PARALLEL_MODE=basic).


---

## VIDEO PLAYBACK FIX + PRO EDITOR (Phase a) — 2026-06 (tested: iteration_9 & iteration_10)

### Bug fix — AI videos wouldn't play (iteration_9, 100%)
- Root cause: `/api/video/{id}/download` returned 200 and ignored the Range header (no Accept-Ranges). Veo mp4s (moov atom at end) wouldn't play in Chrome → stuck at 0:00 black.
- Fix: `_ranged_video_response()` — full HTTP Range support (206 Partial Content + Accept-Ranges + Content-Range). Edited videos also written with `-movflags +faststart`.
- Also added DELETE /api/video/jobs/{id} (delete whole generation) + UI trash button; Social post caption text enlarged (text-base/xl).

### Pro Editor Phase (a) for AI videos (iteration_10 — backend 100%, frontend ~92%)
- `video_editor.py::transform_video()`: ONE-pass FFmpeg — speed (setpts/atempo), reframe 16:9/9:16/1:1 (scale cover + center crop), color looks (cinematic/warm/cool/bw/vivid), PNG logo overlay `overlay=x=(W-w)*xf:y=(H-h)*yf` (position as frame fractions → auto-recomputes on reframe), faststart output.
- Endpoints: POST /video/jobs/{id}/edit → new job kind='edit' stored in object storage (`edited_path`, originals untouched); /me/logo upload+get; /me/preferences GET/PUT (per-user logo position/size/opacity). video_download serves edited_path from object storage with Range.
- Frontend `components/VideoEditor.jsx`: modal with live preview (video + CSS filter + positioned logo img), aspect/filter/speed pills, logo upload + 3x3 grid + X/Y/size/opacity sliders, saved preference, export → new job. Export hardened against transient proxy errors (detects the created job).

### STILL PENDING (user asked "Ambos" for format + Social logo on images)
- P1: Reframe/filter editor on EXPERIENCE CUTS (only AI videos done). video_editor.transform_video is reusable — wire into render_cut_task / a cut-edit endpoint.
- P1: Logo/text overlay on SOCIAL post IMAGES (the current logo editor targets videos).
- P2: Editor Phase (b): visual timeline, trim handles, text/titles, music track.
- Code hygiene: server.py ~983 lines — split into routers (video/editor/files/social/admin) when convenient.


---

## PRO EDITOR v2 + SOCIAL OVERLAYS + PAYPAL — 2026-06 (tested: iteration_13.json, backend 9/9, frontend 100%)

### CapCut-style AI auto-captions (both editors)
- `captions.py` (new): extracts audio via FFmpeg → OpenAI Whisper `whisper-1` (Emergent Universal Key, verbose_json segment timestamps) → builds a styled **ASS** subtitle file (styles: bold / pop / boxed / minimal; auto/es/en). Timings scaled by playback speed. Graceful [] when no speech. Validated end-to-end (TTS→Whisper→ASS→FFmpeg burn).
- `video_editor.py`: `transform_video()` now accepts `subtitle_path` and burns captions with the `ass` filter; added looks **film / noir / vintage / teal_orange** and transitions **fadeblack / fadewhite**.
- `server.py`: `ProEditIn` and `VideoEditIn` gained optional `captions` {enabled,style,lang}; both `/cuts/{id}/pro-edit` and `/video/jobs/{id}/edit` run the caption pipeline before the FFmpeg pass.
- Frontend `CutEditor.jsx` + `VideoEditor.jsx`: captions toggle + style pills + language pills + preview badge; new filter/transition pills.

### Social Studio image overlays (logo + text headline)
- `image_overlay.py` (new): PIL composite of the user logo (position/size/opacity) and a text headline (position/color/size, stroked). Non-destructive — always rebuilt from the original AI image.
- `social.py`: `POST /posts/{id}/overlay` (stores `overlay_path`; clears to revert); `get_design` serves overlay if present; `generate_design` clears stale overlay.
- Frontend `SocialImageEditor.jsx` (new) opened via a "Design/Diseño" button on each post with an image.

### Real PayPal payments (Sandbox) on Pricing
- `payments.py` (new): PayPal REST v2 — `GET /payments/config`, `POST /paypal/create-order`, `POST /paypal/capture`, `GET /history`. Amount computed server-side from the plan catalog; **capture verifies the actual captured amount == expected plan amount** (anti-tamper) and only then upgrades the user's plan + records a payment. Blocking HTTP wrapped in `asyncio.to_thread`.
- Env (backend/.env): `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `PAYPAL_MODE=sandbox`. Validated: create-order returns real sandbox order ids ($49 creator/monthly, $1428 studio/yearly).
- Frontend `Pricing.jsx`: `@paypal/react-paypal-js` PayPalButtons for paid plans (client_id fetched from `/payments/config`); Free = direct switch; falls back to direct switch if PayPal not configured.

### STILL PENDING / NOT DONE
- Real social publishing to Instagram/X/LinkedIn = still SIMULATED. Requires each platform's own developer app + OAuth credentials + platform review (Instagram needs Business acct + FB Page + app review; X API paid tier; LinkedIn Marketing API access). Awaiting user's per-network app credentials.
- PayPal full purchase requires buyer login (can't be automated); capture path is coded + amount-verified but end-to-end purchase pending manual/user test. Currently SANDBOX mode.

---

## FIXES + REAL SCENE TRANSITIONS — 2026-06

### Root-cause fix: transitions / captions / music "not working"
- BUG: still **images** in a cut's EDL were normalized with duration 0.0 (missing `-loop 1`). The scene-transition `xfade` graph then failed ("matches no streams") and the pro-edit **silently fell back** to a plain whole-clip fade — so users saw no real transitions. Images were also effectively dropped from every cut.
- FIX `ffmpeg_worker.normalize_segment`: detect stills (`_is_image`) and render them with `-loop 1 -t dur` + silent audio, min 0.5s. `render_cut_with_transitions` now also drops any sub-0.2s segment and recomputes the crossfade duration defensively.
- Verified on the user's real 4-clip cut (with an image): full combo (transition **fadeblack** + music **coastal-light** + captions **pop** + logo) → `scene_transitions:true`, `captions_status:applied`, audio present (mean −23 dB = music), 12.35s output.
- Music reliability: `storage.get_object` now retries 3× on connection/timeout errors (intermittent object-storage `ConnectTimeout` was dropping music/originals).
- Captions feedback: `/cuts/{id}/pro-edit` and `/video/jobs/{id}/edit` now return `captions_status` = off | applied | no_speech; the editors show a warning toast when no clear speech is detected (captions can't be invented from silent footage).
- Real between-scene transitions confirmed working (xfade video + acrossfade audio) for cuts with ≥2 scenes; single-clip / Veo clips still use whole-clip fade.

### PENDING (next)
- P1: LinkedIn + Instagram real publishing (awaiting user OAuth app credentials — playbooks already retrieved).

---

## B-ROLL INSERTS + FIXES VERIFIED — 2026-06 (tested: iteration_14.json, frontend 100%)

### NEW: Stock/AI B-roll inserts (Cut Pro Editor)
- `inserts.py`: `build_insert_clip` turns a still into a motion clip (kenburns / zoomout / slide / fade / pulse via zoompan + fade), `splice_inserts` splits the base by timestamp and crossfades the insert in/out.
- `inserts_router.py` (`/api/inserts`): `POST /ai` (Gemini via Universal Key), `GET /stock/search` + `POST /stock/save` (Pexels — needs `PEXELS_API_KEY`, currently NOT set → stock disabled, AI works), `GET /` library, `GET /{id}/image` (token via header or `?auth=`), `DELETE /{id}`, `GET /config`. Insert images stored in object storage; collection `insert_assets`.
- `server.py`: `ProEditIn.inserts` [{id, at_sec, duration, effect}] spliced into the base before captions/transform in `pro_edit_cut`. Verified via curl: AI insert generated + spliced (cut 12.35s → 15.1s).
- Frontend `CutEditor.jsx`: B-roll section — AI prompt gen, stock search (gated), your-library grid, and per-insert rows with effect pills + 'At sec' & 'Duration' sliders (max from the preview video duration).

### Root-cause fixes verified this iteration
- Still-image cut segments now loop to full duration → real between-scene xfade transitions no longer silently fall back. `xfade_concat` shared by cut transitions + inserts.
- `captions_status` (off/applied/no_speech) returned + warning toast when footage has no speech.
- `storage.get_object` retries 3× on connection/timeout (fixed intermittent music drop-outs).

### TO ENABLE STOCK (optional)
- Add `PEXELS_API_KEY` to backend/.env (free at pexels.com/api) → the Cut editor stock search activates automatically.

---

## SOCIAL IMAGE STYLE (illustration/infographic, not photos) — 2026-06

- User wants Social images as ILLUSTRATED/INFOGRAPHIC educational graphics (3D/vector characters, title, checklist, brand colors, website footer) — NOT photos of real people — plus the company logo in a corner.
- `social.py`: added `STYLE_PRESETS` (infographic / illustration3d / flatvector / minimal / photo). `generate_design` now leads with the style directive ("STRICTLY NO photorealistic photographs of real people") and frames the AI's design_prompt as the TOPIC; `make_plan` forces design_prompts to follow the chosen style. Brand Kit gains `image_style` + `website`.
- Auto-brand: `generate_design` stamps the logo in a corner (x=0.96,y=0.05) and the website URL at the footer when set. Overlay is now non-fatal (try/except) and PIL uses `LOAD_TRUNCATED_IMAGES=True` (Gemini PNGs were sometimes truncated → fixed OSError broken data stream).
- Verified: generated a real infographic (3D character + title + checklist + purple brand bg + "www.redagilelatam.com" footer + corner logo) — matches the user's references. `/social/brand` returns `styles` list.
- Frontend `SocialStudio.jsx`: Brand Kit now has a Visual Style dropdown (data-testid brand-style) + Website field (brand-website).
- Brand Kit LOGO UPLOAD (2026-06): logo upload + live preview directly in the Brand Kit (data-testid brand-logo-upload / brand-logo-file / brand-logo-preview); uploading auto-enables `auto_logo`. Verified end-to-end: uploaded a "RED AGILE" logo → it is stamped in the top-right corner of the generated infographic, with the website at the footer. (POST /me/logo accepts png/jpeg/webp, stored via storage; served at /me/logo?auth=token.)

---

## EDITOR RESULT PREVIEW + TEXT-ON-VIDEO + TRANSITION SPEED + MUSIC VOL + POSTER STYLES — 2026-06 (tested: iteration_15.json, frontend 100%)

### Root cause of "subtitles/music don't work" = misleading PREVIEW (not a real bug)
- Proven by extracting frames from real exports: subtitles ARE burned, the logo IS stamped, and music IS present (mean ‑23 dB). The editor's PREVIEW only showed a sample caption badge and played the SOURCE's original audio, so users thought it failed.
- Fix: after Apply, `CutEditor` shows a RESULT `<video>` (data-testid cut-editor-result) that plays the exported cut WITH audio + burned subtitles; 'Edit again' (cut-editor-editagain) returns. The source preview is now `muted` + labelled 'Preview · muted', and the caption badge says '(sample) real captions on export'.

### New Cut Pro Editor controls
- Text on video (drawtext, auto-fit to width): top/center/bottom + size. `ProEditIn.text_overlay` {enabled,content,position,size}. Verified frame: "FARMEANDO AURA" burned top.
- Transition speed: slow=1.0 / med=0.5 / fast=0.25s → `transition_speed`; applied to both scene xfade (tdur) and whole-clip fade.
- Music volume slider: `music_volume` (0–1.5). Verified louder at 1.2 (‑20.3 dB vs ‑23 dB).

### Social image styles (poster/badge) matching references
- Added `poster` (bold huge display type + central 3D mascot + solid vivid brand bg + logo top + handle bottom) and `badge` (emblem/seal) to STYLE_PRESETS + STYLE_LABELS. Verified: a "PATAGONIA DREAMING" poster generated with 3D character, red brand bg, brand name top, handle bottom, corner logo — matches the user's Shimaya reference.

### Hardening
- `ffmpeg_worker._run`/`video_editor._run`/`inserts._run` now catch FileNotFoundError/timeout and return a structured failure (a transient `ffprobe` FileNotFoundError during hot-reload previously surfaced as a 500).

---

## OWN-PHOTO UPLOAD + CRISP TEXT OVERLAY + COPY-ONLY + LONGER COPY — 2026-06

- User: AI images inconsistent/ugly for reference-style posts (crisp headline typography). Answer: the reliable path is HYBRID — image (AI OR uploaded) + crisp text WE render (not the AI). Proven: uploaded a photo → sharp yellow 2-line headline (top) + subline (bottom) exactly like the reference.
- `social.py`: `POST /posts/{id}/upload-image` (multipart, re-encoded to PNG) lets users use a real event photo instead of AI. Copy-only already works (image optional). `OverlayIn.texts` list; captions/copy length raised to 150–230 words.
- `image_overlay.apply_overlay`: now accepts a `texts` list of layers, each auto-fit-to-width, wrapped, positioned top/center/bottom with strong outline (headline + subline). Backward compatible with single `text`.
- Frontend: `SocialStudio` adds "Upload photo"/"Replace" (data-testid social-upload-<id>/social-replace-<id>) + "post copy only" hint; the overlay editor button relabelled "Texto + Logo". `SocialImageEditor` now has Headline (top) + Subline (bottom) layers (social-headline-* / social-subline-*), each with position/color/size, sending a `texts` array.
- Verified via curl + rendered PNG: upload photo + headline/subline overlay produces pixel-crisp typography.


## FAL.AI IMAGE ENGINE (Recraft V3 + Ideogram v3) — 2026-06
- fal_images.py: fal.ai via Emergent Universal Key (queue proxy). recraft (fal-ai/recraft/v3/text-to-image + brand palette RGB, style digital_illustration) and ideogram (fal-ai/ideogram/v3). Returns PNG bytes.
- social.py generate_design(engine=): per-post engine (recraft|ideogram|gemini), default brand.image_engine or recraft; Gemini AUTO-FALLBACK on any fal error; stored in object storage. BrandIn.image_engine. Frontend SocialStudio: selector social-engine passed as ?engine=.
- VERIFIED: Recraft produced agency-quality 3D illustration (SHIMAYA/GET LOST), far better than Gemini; stored+served.
- KNOWN ISSUE (next fix): long fal generations can exceed the k8s ingress ~100s timeout -> browser POST returns 504 though the image completes server-side. Needs async job + polling for the design endpoint. NOT yet e2e-tested via testing_agent.
- Then B: verify Veo playback (DONE jobs have empty result_url; playback relies on /video/download/{id} proxy) + admin cost panel.


---

## v2.0 PIVOT — "Comando de Implementación v2.0" (2026-09, IN PROGRESS)
Source: user artifact LUMIERE_Emergent_Build_Command_v2.md. Replaces Master Spec v1.0 on conflict. Execute block-by-block, report PASS/FAIL, don't advance until current block passes. Decisions logged in /app/DECISIONS.md, deferred items in /app/BACKLOG.md.

### Product thesis (drives every UI decision)
LUMIÈRE is the only system that accompanies all 3 phases of a real story: BEFORE (plan) → DURING (direct live capture) → AFTER (understand, evaluate, request missing shot, re-edit, learn). It closes the loop because it can send the human back to shoot. `<PhaseIndicator phase>` must be visible on every screen inside an Experience, and the phase must visibly REGRESS when the user taps GET THE SHOT.

### Block 0 — ELIMINATE ✅ DONE (verified 2026-09-09)
- Removed Social module (SocialStudio, SocialImageEditor, backend social.py/fal_images.py/image_overlay.py, social_router, admin Social tab/monitor/entitlement). Removed free-prompt video screen (CreateVideo). Removed legacy Dashboard.
- D-02 Canva/canvas editor = N/A (never existed; no fabric/konva/canvas deps).
- Primary nav = exactly 5: Home(/studio) · Experiences(/experiences) · Create(/create) · Studio(last exp / /experiences) · Profile(/account). Pricing/Admin hidden (no nav link). No dead 404s (retired routes → catch-all).
- AC PASS: grep social/canvas terms in src = CLEAN; no canvas deps; nav=5; app compiles; backend clean.

### Block 1 — DATA MODEL 🔶 STARTED
- Experience now persists `phase="before"` + v2 fields (location_name/lat/lng, start_date/end_date, target_platform, status enum default DRAFT). Verified via curl. Mongo is schemaless → new collections (story_intents, story_beats, shot_missions, gaps, media_segments, cut_versions/EDL) will be created as their features are built. `provenance` NOT NULL on MediaAsset to be enforced in Block 4 upload.

### REMAINING (next, in doc's priority order)
- P0 **Block 4 (the heart)**: upload → Vision Agent (Gemini, exact prompt) segments → deterministic Story Completeness formula (code scores, AI classifies) → Gap detection (≤3, impact/effort) → SCR-061 Missing Shot (GET THE SHOT → phase regresses to `during`) → re-evaluate → Editor Agent EDL (exact prompt, NEVER include ai_previz) → deterministic FFmpeg render (3 bundled CC0 tracks) → conversational revision (NL→structured params→new child CutVersion, lineage v1→v2).
- P0 **Block 2 (BEFORE)**: SCR-020 New Experience, SCR-021 Story Intent (8 mood chips max3, creator_presence slider), Director Agent POST /api/story/generate (exact prompt, 5-7 beats, 3 critical, deterministic 6-beat fallback), SCR-022/023, Cinematographer POST /api/shots/generate (8-12 missions, exact prompt), Golden Hour Engine (astral, deterministic, ideal_time_computed).
- P0 **Block 3 (DURING)**: SCR-040 Live Director (one mission at a time), deterministic next-shot selection, live re-planning on SKIP of a critical beat, production progress bar, resume-in-place.
- P1 **Block 2.8**: Veo previz → degraded to Gemini reference image, badge "AI REFERENCE", provenance="ai_previz", never in EDL.
- P1 **Block 5**: Agent Trace SCR-095 (timestamp·agent·operation·duration_ms·status·confidence).
- P1 **Block 10**: DEMO_MODE (preloaded /demo_assets, fallback_cut.mp4, cached agent responses, one-click reset).
- Geocoding: Nominatim (UA LumiereStudio/1.0, 1 req/s, 400ms debounce, in-mem cache; fallback free-text + null latlng → generic golden-hour labels).

### Blocks 2 (core) + 3 + 4 + 5 — ✅ DONE (2026-09-09, tested iteration_19 = 100%, 12/12 frontend flows)
Backend curl-verified + frontend testing-agent-verified end to end.
- backend/v2.py (router /api/v2): intent, story (Director, exact prompt, 5-7 beats, exactly 3 critical enforced in code, deterministic fallback), shots (Cinematographer, 8-12 missions) + Golden Hour ideal_time_computed, state, upload (provenance=human_captured), analyze (Vision segments), completeness+gaps (deterministic formula in completeness.py), gaps/{id}/mission (GET THE SHOT → phase REGRESSES to during), next-shot (deterministic selection) + shots/{id}/status (skip critical → alternative mission), build (Editor EDL, ai_previz filtered, FFmpeg render + CC0 music), cuts/{id}/revise (NL→structured params→deterministic new CHILD CutVersion, v1 preserved), trace.
- backend/v2agents.py: exact v2 prompts via Emergent Universal Key (emergentintegrations) — BYPASSES the Agent Engine gateway (whose deployed subagents used a legacy bilingual schema). All fields normalized to plain English.
- backend/sun_time.py (astral) golden hour + window enum normalization. backend/completeness.py deterministic score/gaps.
- Frontend: pages/Experience.jsx rebuilt as the 3-phase workspace (tabs before/during/after), components/PhaseIndicator.jsx (regresses on GET THE SHOT), Live Director (one mission), completeness ring + gaps + Missing Shot, build + video players, conversational revise with version lineage, Agent Trace table. pages/Create.jsx, Experiences.jsx.
- Verified numbers: story 5 beats/3 critical; build 45.6s cinematic; revise "faster,less of me" → 28.2s child; MP4 served at /api/files (206/200).

### REMAINING (v2 P1/P2)
- Block 2.8: Veo previz (degrade to Gemini reference image, badge AI REFERENCE, provenance ai_previz never in EDL) — endpoint scaffold pending.
- Block 2 polish: SCR-020 location autocomplete via Nominatim (UA LumiereStudio/1.0, 1 req/s, 400ms debounce, cache; fallback free-text null latlng). Currently Create takes title/type only; location can be set via API.
- Block 10: DEMO_MODE (preloaded /demo_assets, fallback_cut.mp4, cached agent responses, one-click reset).

### v2 P1/P2 batch — ✅ DONE (2026-09-09, curl-verified + UI smoke-tested)
Order requested by user: DEMO_MODE → title cards → previz → geocoding. All PASS.
- **DEMO_MODE** (backend/.env DEMO_MODE=true): GET /api/v2/demo/config; POST demo/load-footage (synthesizes 3-4 CC0 demo clips into media_assets); POST demo/reset (clears footage/segments/gaps/cuts, phase→before, keeps story+shots) <3s; render FALLBACK cut when render fails in demo (never blank, traced); agent-response cache (demo_agent_cache) reused on LLM failure. Frontend: demo-load-footage + demo-reset buttons (gated by config).
- **Title cards** (Block 4.8): ffmpeg_worker.normalize_segment burns drawtext (LiberationSerif-Bold, lower-third, fade-in); build EDL attaches title_card text, max 3 per film; verified drawtext renders.
- **Previz** (Block 2.8): POST /api/v2/shots/{id}/previz → Gemini image (gemini-3.1-flash-image-preview, Universal Key, 45s cap) → media_asset provenance="ai_previz" (HARD-filtered from every EDL) + shot.previz_asset_id; degrades gracefully. Frontend "Preview shot" button → image with "AI REFERENCE" badge + caption. Verified: 1MB PNG served 200.
- **Geocoding** (backend/geocode.py): single Nominatim call at experience save (UA LumiereStudio/1.0, per-query in-mem cache, 8s timeout); NO autocomplete. Free-text location in Create.jsx. Verified: "Lisbon, Portugal"→(38.708,-9.137); gibberish→(null,null) → Golden Hour falls back to generic labels.

### STILL REMAINING (optional polish)
- SCR-020/021/022/023 as separate onboarding screens (currently unified in workspace Before tab; onboarding ≤3 steps satisfied).
- Real Veo (swap previz Gemini→Veo when Cloud Run gateway /video is redeployed).

### Final batch (2026-09-09) — Share Film + Session expiry + Demo scaffold. CODE FROZEN.
- **Session expiry = 1 hour** (auth.py SESSION_TTL=1h; cookie max_age=3600; expiry already enforced in get_current_user → 401). Frontend api.js response interceptor auto-logs-out on 401 (excludes /auth/me probe + public routes /,/login,/share). Verified: valid token=200, expired=401.
- **Share Film — PASS**: POST /api/v2/cuts/{id}/share (creates share_id + ffmpeg poster). Public (no-auth) public_router: GET /api/public/cuts/{share_id} (meta), /video (range), /poster. Frontend: Share button + copyable link on each cut; public page /share/:shareId (Share.jsx, outside Protected). Verified E2E incl. browser render.
- **Demo scaffold — WAITING ON REAL CLIPS**: /app/demo_assets/ (README added). demo/load-footage reads REAL clips from that folder (NO synthesized bars); returns a hint if empty. GET demo/config reports demo_assets_ready. Render fail-safe uses /app/demo_assets/fallback_cut.mp4 ONLY if present. TODO once user drops clips: wire the seeded Lisbon demo experience.
- OUT OF SCOPE per user: Veo Real, separate Onboarding Screens.

### Shot List flexibility (2026-09-09) — DONE, self-tested (curl + screenshot)
User request: "Se podrían también traducir, modificar y cambiar con IA Generativa los shot list" — give the Shot List (tomas) the same control as the Story Arc beats. User choices: edit + translate + AI-regenerate (all); translate button translates EVERYTHING together (arc + shots); keep whole-list regenerate (↻) AND add per-shot AI regenerate.
- Backend `v2agents.py`: `TRANSLATE_SYS` prompt extended to translate shot fields (action/composition_note/narrative_purpose); new `CINE_ONE_SYS` + `regenerate_one_shot(exp, beat, prev_action)` agent (generates ONE alt mission, asks for a clearly different approach when re-rolling a confusing shot).
- Backend `v2.py`: new `POST /api/v2/shots/{shot_id}/regenerate` (re-rolls one shot via Cinematographer, recomputes Golden Hour window/label, returns updated shot). `POST /experiences/{id}/translate` already fanned shots into the payload — now the prompt actually translates them.
- Frontend `Experience.jsx`: Shot cards now show on-hover edit (Pencil, inline textarea + Save/Cancel), regenerate (Sparkles, iris, per-shot loading), delete (Trash). Added `regenShot`/`regenShotId`. testids: `edit-shot-<id>`, `regen-shot-<id>`, `shot-edit-action-<id>`, `shot-save-<id>`, `delete-shot-<id>`. Existing `regen-shots` (↻) still regenerates the full list.
- Verified: PATCH edit persists; translate→shots rendered in Spanish; regenerate returns a new distinct action + fresh golden-hour time; hover UI confirmed via screenshot on exp 25ee6af7.

### Grafana Cloud partner track — agent observability (2026-09-09) — DONE, self-tested
Prometheus `remote_write` push of LUMIÈRE agent metrics to Grafana Cloud. HARD requirement met: emission is fire-and-forget and FAILS SILENTLY (warns + continues); never blocks a user operation.
- `backend/services/grafana_metrics.py`: self-contained sender — minimal pure-Python Prometheus `remote_write` protobuf encoder + `cramjam` snappy RAW block compression + async `httpx` POST (Basic Auth: instance_id / API token). In-process cumulative state so counters are monotonic and histogram buckets cumulative. `_fire()` schedules via `asyncio.create_task` (or a daemon thread if no loop). Every path wrapped so nothing escapes.
- Metrics: `lumiere_agent_duration_ms` (histogram, label agent), `lumiere_agent_calls_total` (counter, labels agent+status), `lumiere_agent_confidence` (gauge, label agent), `lumiere_story_completeness` (gauge, label experience_id).
- Emission point = the SINGLE Agent-Trace sink: `agents.py::_persist_run` calls `record_agent(...)`. An allowlist restricts emission to exactly the six spec agents: Director, Cinematographer, Vision, Evaluator, Editor, Render Worker (Translator/Sun Engine/Reviser/Context are skipped). `v2.py::_recompute` calls `record_completeness(exp_id, score)` (Evaluator point).
- Credentials (env, currently EMPTY placeholders in backend/.env → integration is a silent no-op until set): `GRAFANA_CLOUD_REMOTE_WRITE_URL`, `GRAFANA_CLOUD_INSTANCE_ID`, `GRAFANA_CLOUD_API_TOKEN` (Cloud Access Policy token, scope metrics:write).
- Dep added: `cramjam==2.12.1` (frozen into requirements.txt).
- Tested (`backend/test_grafana.py`, all PASS): allowlist (6 emitted, others skipped); protobuf+snappy roundtrip decodes to correct names/labels/values; monotonic counter + cumulative histogram across calls; completeness gauge; `_send` to an unreachable host returns WITHOUT raising (ConnectError only logged); not-configured no-op. Live regenerate flow through `_persist_run` unaffected.

### Grafana Cloud — ACTIVATED + verified (2026-09-09). CODE FROZEN.
- Credentials loaded in `backend/.env` (write token, stack-1718998, prometheus-prod-67-prod-us-west-0). `.env` confirmed in `.gitignore` (git check-ignore = ignored, NOT tracked → never reaches the public repo).
- Ran a FULL live agent flow (new exp `1bb5b562...`): Director (6 beats) → Cinematographer (10 shots) → demo footage (4 clips) → Vision (4 analyzed) → Evaluator (completeness 56) → Editor + Render Worker (cut rendered). All six emission points fired.
- Ingestion confirmed with NO 401/403: raw `remote_write` POST returned **HTTP 200**; the running app logged `GRAFANA_SEND_OK status=200 series=15` (temp debug, since reverted); zero "metrics dropped" warnings. (A read-query returns 401 only because the supplied token is `metrics:write`-scoped — not an ingestion issue.)
- Dashboard: `grafana/lumiere_dashboard.json` (+ `grafana/README.md`) — panels: p95 duration/agent, agent failure rate, total calls by status, story completeness by experience; vars `datasource` + `agent`.

### Delete experiences from Home (2026-09-09) — DONE, self-tested (curl + screenshot)
User request: "Deberían poder eliminarse los videos que aparecen aquí" (the experience cards on Home/Studio).
- Reused existing `DELETE /api/experiences/{exp_id}` (soft-trash by default: sets status=trashed, preserves originals, removes from list + frees the plan counter which filters status!=trashed).
- Frontend `Home.jsx`: trash button on the Active Experience card (`delete-active-<id>`) and on each Recent card (`delete-experience-<id>`, shown on hover; recent card refactored from `motion.button` to `motion.div` + inner nav button to avoid nested buttons). Bilingual confirm via shadcn `AlertDialog` (`delete-experience-dialog`, `delete-confirm`/`delete-cancel`). i18n keys added (deleteExp/deleteExpTitle/deleteExpBody/deletedExp, EN+ES).
- Verified: create→delete→gone from `/experiences` (returns `experience_trash`); confirm dialog + buttons render on Home (screenshot).

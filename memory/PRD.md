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

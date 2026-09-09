# LUMIÈRE v2.0 — DECISIONS

Choices made while executing the v2.0 Build Command (simplest option that meets the acceptance criteria).

## Block 0 — Eliminate
- **D-02 (Canva/canvas editor):** N/A — no canvas engine ever existed (no fabric/konva/canvas/sticker/layer deps). Nothing to remove.
- **Primary nav = exactly 5:** Home (`/studio`), Experiences (`/experiences`), Create (`/create`), Studio (opens last/most-recent experience, else `/experiences`), Profile (`/account`). Labels in English.
- **Kept `/studio` as the HOME dashboard route** (not renamed) because the Emergent Google OAuth redirect URL is registered as `origin + /studio`; renaming would break auth.
- **Removed:** Social module (pages/SocialStudio, components/SocialImageEditor, backend/social.py, backend/fal_images.py, backend/image_overlay.py, social_router include), free-prompt video screen (pages/CreateVideo), legacy pages/Dashboard. Admin panel's Social tab + social-posts monitor + Social entitlement toggle removed.
- **Pricing & Admin** are hidden routes (no primary-nav link). Reachable via "Manage plan" buttons (Pricing) and avatar dropdown (Admin, admins only). Retired paths (`/social`, `/create-video`) fall through the router catch-all → `/`.
- **PayPal/Pricing kept** (not in the doc's removal list).
- **i18n:** existing ES/EN infra kept; new v2 screens are authored in English per doc rule 6. Full ES→EN copy migration deferred to BACKLOG.

## Geocoding (Block 2)
- Nominatim (OpenStreetMap), header `User-Agent: LumiereStudio/1.0`, max 1 req/s, 400ms input debounce, in-memory per-query cache. On failure/timeout → free-text place with null lat/lng; Golden Hour Engine falls back to generic labels.

## Previz (Block 2.8)
- Veo gateway `/video` not deployed → previz reference generated with Gemini (Nano Banana, Universal Key), badge "AI REFERENCE". Swap to real Veo when the gateway is redeployed.

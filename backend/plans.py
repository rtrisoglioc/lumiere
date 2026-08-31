"""Configurable plan catalog (defaults). Prices, limits, quotas and entitlements
are placeholders — editable at runtime from the Admin panel (stored in DB via
plans_store). No real payment processing is wired.

entitlements:
  - video:  can invoke AI Video Generation (Vertex/Veo). ENFORCED in backend.
  - social: can access the AI Social Content Studio. ENFORCED in backend.
limits.ai_generations = monthly Veo video quota.
"""

PLANS_VERSION = 3

PLANS = [
    {
        "id": "free",
        "name": "LUMIÈRE FREE",
        "recommended": False,
        "price": {"monthly": 0, "yearly": 0, "currency": "USD"},
        "tagline": {
            "en": "Planning and Detect Gap. Bilingual. No AI video generation.",
            "es": "Planeación y Detect Gap. Bilingüe. Sin generación de video IA.",
        },
        "limits": {"experiences": 2, "cuts": 5, "ai_generations": 0},
        "entitlements": {"video": False, "social": False},
        "features": [
            {"en": "Story planning & shot missions", "es": "Planeación de historia y misiones"},
            {"en": "Detect Gap coverage", "es": "Cobertura Detect Gap"},
            {"en": "Bilingual ES/EN", "es": "Bilingüe ES/EN"},
            {"en": "No AI video generation", "es": "Sin generación de video IA"},
        ],
    },
    {
        "id": "creator",
        "name": "LUMIÈRE CREATOR",
        "recommended": True,
        "price": {"monthly": 49, "yearly": 468, "currency": "USD"},
        "tagline": {
            "en": "Real AI video with Vertex Veo, limited monthly quota.",
            "es": "Video IA real con Vertex Veo, cuota mensual limitada.",
        },
        "limits": {"experiences": 25, "cuts": 200, "ai_generations": 20},
        "entitlements": {"video": True, "social": False},
        "features": [
            {"en": "Everything in Free", "es": "Todo lo de Free"},
            {"en": "AI Video Generation (Veo)", "es": "Generación de Video IA (Veo)"},
            {"en": "20 clips / month", "es": "20 clips / mes"},
            {"en": "Priority rendering", "es": "Renderizado prioritario"},
        ],
    },
    {
        "id": "studio",
        "name": "LUMIÈRE STUDIO",
        "recommended": False,
        "price": {"monthly": 149, "yearly": 1428, "currency": "USD"},
        "tagline": {
            "en": "Expanded video quota + full AI Social Content Studio.",
            "es": "Cuota de video ampliada + AI Social Content Studio completo.",
        },
        "limits": {"experiences": 1000, "cuts": 5000, "ai_generations": 100},
        "entitlements": {"video": True, "social": True},
        "features": [
            {"en": "Everything in Creator", "es": "Todo lo de Creator"},
            {"en": "Expanded video quota", "es": "Cuota de video ampliada"},
            {"en": "AI Social Content Studio", "es": "AI Social Content Studio"},
            {"en": "Auto post plan + scheduling", "es": "Plan de posts + programación"},
        ],
    },
]

FAQ = [
    {
        "q": {"en": "How do the agents make decisions?", "es": "¿Cómo toman decisiones los agentes?"},
        "a": {"en": "Every stage runs on Google Gemini via Vertex AI with full traceability.",
              "es": "Cada etapa corre en Google Gemini vía Vertex AI con trazabilidad total."},
    },
    {
        "q": {"en": "Is my footage private?", "es": "¿Mi material es privado?"},
        "a": {"en": "Yes. Experiences are private by default and originals are never modified.",
              "es": "Sí. Las Experiencias son privadas por defecto y los originales nunca se modifican."},
    },
    {
        "q": {"en": "Can I change plans anytime?", "es": "¿Puedo cambiar de plan cuando quiera?"},
        "a": {"en": "Yes, upgrade or downgrade at any time. Placeholder billing for now.",
              "es": "Sí, mejora o baja de plan cuando quieras. Facturación de placeholder por ahora."},
    },
]


def get_plan(plan_id: str) -> dict:
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    return PLANS[0]

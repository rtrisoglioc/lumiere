"""Configurable plan catalog (PLACEHOLDERS — not final business decisions).

Prices, limits and entitlements are placeholders meant to be edited freely.
No real payment processing is wired.
"""

PLANS_VERSION = 1

PLANS = [
    {
        "id": "free",
        "name": "LUMIÈRE FREE",
        "recommended": False,
        "price": {"monthly": 0, "yearly": 0, "currency": "USD"},
        "tagline": {
            "en": "Explore LUMIÈRE with limited Experiences and AI/media processing.",
            "es": "Explora LUMIÈRE con Experiencias y procesamiento de IA/medios limitados.",
        },
        "limits": {"experiences": 2, "cuts": 5, "ai_generations": 1},
        "features": [
            {"en": "Up to 2 Experiences", "es": "Hasta 2 Experiencias"},
            {"en": "Story planning & shot missions", "es": "Planificación de historia y misiones de toma"},
            {"en": "Gemini footage analysis", "es": "Análisis de material con Gemini"},
            {"en": "1 real rendered cut", "es": "1 corte real renderizado"},
        ],
    },
    {
        "id": "creator",
        "name": "LUMIÈRE CREATOR",
        "recommended": True,
        "price": {"monthly": 24, "yearly": 228, "currency": "USD"},
        "tagline": {
            "en": "For creators producing cinematic travel and lifestyle stories regularly.",
            "es": "Para creadores que producen historias cinematográficas de viaje y lifestyle con frecuencia.",
        },
        "limits": {"experiences": 25, "cuts": 200, "ai_generations": 50},
        "features": [
            {"en": "25 Experiences", "es": "25 Experiencias"},
            {"en": "Higher media limits", "es": "Límites de medios más altos"},
            {"en": "Advanced cuts & conversational re-editing", "es": "Cortes avanzados y re-edición conversacional"},
            {"en": "Visual DNA", "es": "Visual DNA"},
            {"en": "Priority AI processing", "es": "Procesamiento de IA prioritario"},
        ],
    },
    {
        "id": "pro",
        "name": "LUMIÈRE PRO",
        "recommended": False,
        "price": {"monthly": 59, "yearly": 564, "currency": "USD"},
        "tagline": {
            "en": "For professional creators and future brand/hospitality collaboration.",
            "es": "Para creadores profesionales y futura colaboración con marcas/hospitalidad.",
        },
        "limits": {"experiences": 1000, "cuts": 5000, "ai_generations": 1000},
        "features": [
            {"en": "Unlimited-scale Experiences", "es": "Experiencias a escala ilimitada"},
            {"en": "Advanced Visual DNA", "es": "Visual DNA avanzado"},
            {"en": "Experience Intelligence", "es": "Experience Intelligence"},
            {"en": "Future Brand DNA capabilities", "es": "Futuras capacidades de Brand DNA"},
            {"en": "Highest media & AI limits", "es": "Los límites más altos de medios e IA"},
        ],
    },
]

FAQ = [
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
    {
        "q": {"en": "What makes LUMIÈRE different?", "es": "¿Qué hace diferente a LUMIÈRE?"},
        "a": {"en": "Other AI tools edit what you captured. LUMIÈRE helps you understand what to capture next.",
              "es": "Otras herramientas de IA editan lo que capturaste. LUMIÈRE te ayuda a entender qué capturar después."},
    },
]


def get_plan(plan_id: str) -> dict:
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    return PLANS[0]

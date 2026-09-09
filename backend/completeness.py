"""Deterministic Story Completeness + Gap detection (NO AI scores here).

The Vision Agent CLASSIFIES segments; this module SCORES them with a fixed,
reproducible formula so a demo yields the same number for the same input.
"""

REQUIRED_VISUAL_TYPES = {"establishing", "wide", "medium", "close", "detail", "atmosphere"}

# feeling_tag (StoryIntent) -> segment emotion_tag (Vision) synonyms
FEELING_TO_EMOTION = {
    "curious": {"curiosity", "wonder"},
    "free": {"freedom"},
    "elegant": {"calm"},
    "warm": {"intimacy", "calm"},
    "energetic": {"energy"},
    "intimate": {"intimacy"},
    "nostalgic": {"calm", "wonder"},
    "bold": {"energy", "freedom"},
}


def _beat_covered(beat, segments, threshold):
    bid = beat["beat_id"]
    for s in segments:
        if bid in (s.get("beat_candidates") or []) and (s.get("narrative_relevance") or 0) >= threshold:
            return True
    return False


def _beat_partial(beat, segments):
    bid = beat["beat_id"]
    return any(bid in (s.get("beat_candidates") or []) for s in segments)


def compute_completeness(beats, segments, intent, captured_shot_types=None):
    critical = [b for b in beats if b.get("criticality") == "critical"]
    supporting = [b for b in beats if b.get("criticality") != "critical"]

    crit_cov = [b for b in critical if _beat_covered(b, segments, 0.6)]
    supp_cov = [b for b in supporting if _beat_covered(b, segments, 0.5)]

    narrative = 0.0
    if critical:
        narrative += 0.75 * (len(crit_cov) / len(critical))
    else:
        narrative += 0.75
    if supporting:
        narrative += 0.25 * (len(supp_cov) / len(supporting))
    else:
        narrative += 0.25

    # Visual coverage: distinct required shot types present among captured missions.
    present = set(t for t in (captured_shot_types or []) if t in REQUIRED_VISUAL_TYPES)
    if not present:
        # fallback proxy: approximate distinct types by usable segment count
        usable = [s for s in segments if (s.get("usability_score") or 0) >= 0.6]
        present = set(list(REQUIRED_VISUAL_TYPES)[:min(6, len(usable))])
    visual = len(present) / 6.0

    # Emotional coverage: intent feelings present in segment emotion_tags.
    feelings = [f for f in (intent.get("feeling_tags") or [])]
    seg_emotions = set()
    for s in segments:
        seg_emotions.update(s.get("emotion_tags") or [])
    if feelings:
        hit = sum(1 for f in feelings if FEELING_TO_EMOTION.get(f, {f}) & seg_emotions)
        emotional = hit / len(feelings)
    else:
        emotional = 1.0

    score = round(100 * (0.45 * narrative + 0.30 * visual + 0.25 * emotional))
    all_critical_covered = len(crit_cov) == len(critical) and len(critical) > 0
    if score >= 80 and all_critical_covered:
        status = "COMPLETE"
    else:
        status = "IN_PROGRESS"

    coverage = {}
    for b in beats:
        bid = b["beat_id"]
        if _beat_covered(b, segments, 0.6 if b.get("criticality") == "critical" else 0.5):
            coverage[bid] = "covered"
        elif _beat_partial(b, segments):
            coverage[bid] = "partial"
        else:
            coverage[bid] = "empty"

    return {
        "score": score,
        "status": status,
        "narrative": round(narrative, 3),
        "visual": round(visual, 3),
        "emotional": round(emotional, 3),
        "critical_covered": len(crit_cov),
        "critical_total": len(critical),
        "all_critical_covered": all_critical_covered,
        "coverage": coverage,
    }


def detect_gaps(beats, segments, story_id, max_gaps=3):
    gaps = []
    for b in beats:
        bid = b["beat_id"]
        covered = _beat_covered(b, segments, 0.6 if b.get("criticality") == "critical" else 0.5)
        partial = _beat_partial(b, segments)
        if covered:
            continue
        is_crit = b.get("criticality") == "critical"
        if is_crit and not partial:
            impact = 1.0
        elif is_crit and partial:
            impact = 0.7
        elif not is_crit and not partial:
            impact = 0.4
        else:
            continue
        effort = 0.8  # assume it needs returning to the location
        gaps.append({
            "story_id": story_id,
            "beat_id": bid,
            "dimension": "narrative",
            "missing_function": b.get("function"),
            "beat_label": b.get("label"),
            "why_it_matters": b.get("purpose"),
            "impact_score": impact,
            "effort_score": effort,
            "rank": impact / effort,
            "status": "open",
        })
    gaps.sort(key=lambda g: g["rank"], reverse=True)
    return gaps[:max_gaps]

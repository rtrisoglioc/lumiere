"""Golden Hour Engine — deterministic sun-time computation (NO AI).

Given lat/lng/date, computes sunrise/sunset and the golden/blue-hour windows,
then resolves a ShotMission's ideal_time_window label to a real timestamp
(ideal_time_computed). Falls back gracefully to None when location is unknown.
"""
from datetime import datetime, timezone, timedelta

from astral import LocationInfo
from astral.sun import sun, golden_hour, blue_hour, SunDirection


def compute_windows(lat, lng, date_str=None):
    if lat is None or lng is None:
        return None
    try:
        d = datetime.fromisoformat(str(date_str)).date() if date_str else datetime.now(timezone.utc).date()
    except Exception:
        d = datetime.now(timezone.utc).date()
    try:
        obs = LocationInfo(latitude=float(lat), longitude=float(lng)).observer
        s = sun(obs, date=d, tzinfo=timezone.utc)
        gh_am = golden_hour(obs, date=d, direction=SunDirection.RISING, tzinfo=timezone.utc)
        gh_pm = golden_hour(obs, date=d, direction=SunDirection.SETTING, tzinfo=timezone.utc)
        bh = blue_hour(obs, date=d, direction=SunDirection.SETTING, tzinfo=timezone.utc)
    except Exception:
        return None
    sunrise, sunset, noon = s["sunrise"], s["sunset"], s["noon"]
    return {
        "sunrise": sunrise, "sunset": sunset, "noon": noon,
        "golden_hour_am": gh_am[0], "golden_hour_pm": gh_pm[0], "blue_hour": bh[0],
        "morning": sunrise + timedelta(minutes=90),
        "midday": noon,
        "afternoon": noon + timedelta(hours=3),
        "night": sunset + timedelta(hours=2),
    }


def resolve_time(window_label, windows):
    """Return an ISO timestamp for the ideal window, or None when not computable."""
    if not windows or not window_label or window_label == "any":
        return None
    dt = windows.get(window_label)
    if dt is None:
        return None
    if isinstance(dt, tuple):
        dt = dt[0]
    return dt.astimezone(timezone.utc).isoformat()


WINDOW_ENUM = ["golden_hour_am", "morning", "midday", "afternoon", "golden_hour_pm", "blue_hour", "night", "any"]


def normalize_window(raw):
    """Coerce whatever the model returned into one of the enum windows."""
    if not raw:
        return "any"
    low = str(raw).strip().lower()
    if low in WINDOW_ENUM:
        return low
    if "golden" in low:
        return "golden_hour_pm" if any(k in low for k in ("pm", "sunset", "evening", "dusk")) else "golden_hour_am"
    if "blue" in low:
        return "blue_hour"
    if "night" in low:
        return "night"
    if "afternoon" in low:
        return "afternoon"
    if "noon" in low or "midday" in low:
        return "midday"
    if "morning" in low or "sunrise" in low or "dawn" in low:
        return "morning"
    import re
    m = re.search(r"(\d{1,2})", low)
    if m:
        h = int(m.group(1))
        if "pm" in low and h < 12:
            h += 12
        if h <= 7:
            return "golden_hour_am"
        if h <= 10:
            return "morning"
        if h <= 14:
            return "midday"
        if h <= 17:
            return "afternoon"
        if h <= 19:
            return "golden_hour_pm"
        return "night"
    return "any"


def label_time(iso_str):
    """Human 'Golden hour · 6:42 AM' style label from an ISO timestamp."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%-I:%M %p")
    except Exception:
        return None

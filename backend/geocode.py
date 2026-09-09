"""Single-shot geocoding via Nominatim (OpenStreetMap). NO autocomplete.

Called once when an Experience is saved to resolve a free-text place into
lat/lng. On any failure returns (None, None) so Golden Hour degrades to generic
labels without blocking. Per-query in-memory cache; one blocking call (<=1/s).
"""
import requests

_CACHE = {}


def geocode(place: str):
    if not place or not place.strip():
        return (None, None)
    key = place.strip().lower()
    if key in _CACHE:
        return _CACHE[key]
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": place, "format": "json", "limit": 1},
                         headers={"User-Agent": "LumiereStudio/1.0"}, timeout=8)
        r.raise_for_status()
        arr = r.json()
        res = (float(arr[0]["lat"]), float(arr[0]["lon"])) if arr else (None, None)
    except Exception:
        res = (None, None)
    _CACHE[key] = res
    return res

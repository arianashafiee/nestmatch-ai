import math
import re
from typing import Optional
from urllib.parse import quote

import httpx

from app.config import settings
from app.services.listing_fetcher import BROWSER_HEADERS

GEOCODE_CACHE: dict[str, Optional[tuple[float, float]]] = {}

COMMUTE_SPEED_MPH = {
    "walking": 3.0,
    "biking": 10.0,
    "transit": 18.0,
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(a))


def estimate_commute_minutes(distance_miles: float, mode: str) -> int:
    speed = COMMUTE_SPEED_MPH.get(mode, COMMUTE_SPEED_MPH["walking"])
    if distance_miles <= 0:
        return 0
    return max(1, int(round(distance_miles / speed * 60)))


def max_commute_radius_miles(max_minutes: int, mode: str) -> float:
    speed = COMMUTE_SPEED_MPH.get(mode, COMMUTE_SPEED_MPH["walking"])
    return max_minutes / 60.0 * speed


def _cache_key(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


def geocode(query: str) -> Optional[tuple[float, float]]:
    """Resolve an address or place name to (lat, lng)."""
    key = _cache_key(query)
    if not key:
        return None
    if key in GEOCODE_CACHE:
        return GEOCODE_CACHE[key]

    coords: Optional[tuple[float, float]] = None
    if settings.mapbox_access_token:
        coords = _geocode_mapbox(query)
    if coords is None:
        coords = _geocode_nominatim(query)

    GEOCODE_CACHE[key] = coords
    return coords


def _geocode_mapbox(query: str) -> Optional[tuple[float, float]]:
    token = settings.mapbox_access_token
    if not token:
        return None
    url = (
        "https://api.mapbox.com/geocoding/v5/mapbox.places/"
        f"{quote(query)}.json"
    )
    try:
        with httpx.Client(timeout=12, follow_redirects=True) as client:
            response = client.get(
                url,
                params={
                    "access_token": token,
                    "country": "us",
                    "limit": 1,
                },
            )
            response.raise_for_status()
            features = response.json().get("features") or []
            if not features:
                return None
            lng, lat = features[0]["center"]
            return float(lat), float(lng)
    except Exception:
        return None


def _geocode_nominatim(query: str) -> Optional[tuple[float, float]]:
    headers = {
        **BROWSER_HEADERS,
        "User-Agent": "NestMatchAI/1.0 (campus apartment search)",
    }
    try:
        with httpx.Client(headers=headers, timeout=12, follow_redirects=True) as client:
            response = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                return None
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        return None

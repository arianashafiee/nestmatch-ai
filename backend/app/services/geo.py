import math
import re
from typing import Optional
from urllib.parse import quote

import httpx

from app.config import settings
from app.services.listing_fetcher import BROWSER_HEADERS

GEOCODE_CACHE: dict[str, Optional[tuple[float, float]]] = {}
DIRECTIONS_CACHE: dict[str, Optional[tuple[float, float, float]]] = {}

METERS_TO_MILES = 0.000621371
MAPBOX_MATRIX_MAX_COORDS = 25

COMMUTE_SPEED_MPH = {
    "walking": 3.0,
    "biking": 10.0,
    "transit": 18.0,
    "driving": 25.0,
}

MAPBOX_DIRECTIONS_PROFILE = {
    "walking": "walking",
    "driving": "driving",
    "biking": "cycling",
    "transit": "driving",
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


def mapbox_directions_profile(commute_mode: str) -> str:
    return MAPBOX_DIRECTIONS_PROFILE.get(commute_mode, "walking")


def _commute_from_route(
    distance_meters: float,
    duration_seconds: float,
    commute_mode: str,
) -> tuple[float, int]:
    distance_miles = round(distance_meters * METERS_TO_MILES, 2)
    if commute_mode == "transit":
        minutes = estimate_commute_minutes(distance_miles, "transit")
    else:
        minutes = max(1, int(round(duration_seconds / 60)))
    return distance_miles, minutes


def _directions_cache_key(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    commute_mode: str,
) -> str:
    profile = mapbox_directions_profile(commute_mode)
    return (
        f"{profile}|{origin_lat:.5f},{origin_lng:.5f}|"
        f"{dest_lat:.5f},{dest_lng:.5f}"
    )


def mapbox_route_commute(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    commute_mode: str,
) -> Optional[tuple[float, int]]:
    """Route distance (mi) and travel time (min) via Mapbox Directions."""
    token = settings.mapbox_access_token
    if not token:
        return None

    cache_key = _directions_cache_key(
        origin_lat, origin_lng, dest_lat, dest_lng, commute_mode
    )
    if cache_key in DIRECTIONS_CACHE:
        cached = DIRECTIONS_CACHE[cache_key]
        if cached is None:
            return None
        distance_miles, minutes, _duration = cached
        return distance_miles, int(minutes)

    profile = mapbox_directions_profile(commute_mode)
    coordinates = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = (
        "https://api.mapbox.com/directions/v5/mapbox/"
        f"{profile}/{coordinates}"
    )
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(
                url,
                params={
                    "access_token": token,
                    "overview": "false",
                    "alternatives": "false",
                },
            )
            response.raise_for_status()
            routes = response.json().get("routes") or []
            if not routes:
                DIRECTIONS_CACHE[cache_key] = None
                return None
            route = routes[0]
            distance_meters = float(route["distance"])
            duration_seconds = float(route["duration"])
            distance_miles, minutes = _commute_from_route(
                distance_meters, duration_seconds, commute_mode
            )
            DIRECTIONS_CACHE[cache_key] = (
                distance_miles,
                float(minutes),
                duration_seconds,
            )
            return distance_miles, minutes
    except Exception:
        DIRECTIONS_CACHE[cache_key] = None
        return None


def mapbox_batch_route_commutes(
    campus_lat: float,
    campus_lng: float,
    destinations: list[tuple[int, float, float]],
    commute_mode: str,
) -> dict[int, tuple[float, int]]:
    """Batch route commutes from campus to many listings via Mapbox Matrix."""
    token = settings.mapbox_access_token
    if not token or not destinations:
        return {}

    profile = mapbox_directions_profile(commute_mode)
    results: dict[int, tuple[float, int]] = {}
    chunk_size = MAPBOX_MATRIX_MAX_COORDS - 1

    for chunk_start in range(0, len(destinations), chunk_size):
        chunk = destinations[chunk_start : chunk_start + chunk_size]
        coords = [(campus_lat, campus_lng)] + [(lat, lng) for _, lat, lng in chunk]
        coord_str = ";".join(f"{lng},{lat}" for lat, lng in coords)
        destination_indices = ";".join(str(index) for index in range(1, len(coords)))

        url = (
            "https://api.mapbox.com/directions-matrix/v1/mapbox/"
            f"{profile}/{coord_str}"
        )
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                response = client.get(
                    url,
                    params={
                        "access_token": token,
                        "sources": "0",
                        "destinations": destination_indices,
                        "annotations": "distance,duration",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                distances = payload.get("distances") or []
                durations = payload.get("durations") or []
                if not distances or not durations:
                    continue

                row_distances = distances[0]
                row_durations = durations[0]
                for index, (listing_id, _, _) in enumerate(chunk):
                    if index >= len(row_distances) or index >= len(row_durations):
                        continue
                    distance_meters = row_distances[index]
                    duration_seconds = row_durations[index]
                    if distance_meters is None or duration_seconds is None:
                        continue
                    results[listing_id] = _commute_from_route(
                        float(distance_meters),
                        float(duration_seconds),
                        commute_mode,
                    )
        except Exception:
            continue

    return results


def commute_between_coords(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    commute_mode: str,
) -> Optional[tuple[float, int]]:
    """Prefer Mapbox route distance/time; fall back to straight-line estimate."""
    routed = mapbox_route_commute(
        origin_lat, origin_lng, dest_lat, dest_lng, commute_mode
    )
    if routed is not None:
        return routed

    distance = haversine_miles(origin_lat, origin_lng, dest_lat, dest_lng)
    minutes = estimate_commute_minutes(distance, commute_mode)
    return round(distance, 2), minutes


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

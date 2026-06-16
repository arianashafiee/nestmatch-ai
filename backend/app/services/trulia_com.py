"""Trulia rental search fallback (Zillow network — HTML blocked on zillow.com)."""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from app.services.image_quality import normalize_photo_list
from app.services.location_parse import ParsedLocation

TRULIA_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}


def _trulia_search_url(parsed: ParsedLocation) -> str:
    if parsed.is_usable_for_search:
        city = parsed.city.replace(" ", "-")
        return f"https://www.trulia.com/for_rent/{city},{parsed.state.upper()}/"
    slug = re.sub(r"\s+", "-", parsed.raw.strip())
    return f"https://www.trulia.com/for_rent/{slug}/"


def _extract_trulia_payload(html: str) -> Optional[dict]:
    marker = html.rfind('{"props":')
    if marker < 0:
        return None
    end = html.find("</script>", marker)
    if end < 0:
        return None
    try:
        return json.loads(html[marker:end])
    except json.JSONDecodeError:
        return None


def _rent_from_home(home: dict) -> Optional[float]:
    price = home.get("price")
    if isinstance(price, dict):
        for key in ("formatted", "min", "max", "value"):
            raw = price.get(key)
            if isinstance(raw, (int, float)):
                return float(raw)
            if isinstance(raw, str):
                digits = re.sub(r"[^\d.]", "", raw)
                if digits:
                    return float(digits)
    elif isinstance(price, (int, float)):
        return float(price)
    elif isinstance(price, str):
        digits = re.sub(r"[^\d.]", "", price)
        if digits:
            return float(digits)
    return None


def _photo_from_home(home: dict) -> list[str]:
    photos: list[str] = []
    metadata = home.get("metadata") or {}
    if isinstance(metadata, dict):
        for key in ("photo", "photoUrl", "primaryPhoto", "heroImage"):
            val = metadata.get(key)
            if isinstance(val, str) and val.startswith("http"):
                photos.append(val)
        for photo in metadata.get("photos") or []:
            if isinstance(photo, str) and photo.startswith("http"):
                photos.append(photo)
            elif isinstance(photo, dict) and photo.get("url"):
                photos.append(str(photo["url"]))
    return normalize_photo_list(photos, "zillow.com", limit=3)


def parse_trulia_search(html: str, base_url: str) -> list[dict]:
    payload = _extract_trulia_payload(html)
    if not payload:
        return []

    search_data = (payload.get("props") or {}).get("searchData") or {}
    homes = search_data.get("homes") or []
    results: list[dict] = []
    seen_urls: set[str] = set()

    for home in homes:
        if not isinstance(home, dict):
            continue
        listing_path = home.get("url") or home.get("homeUrl") or ""
        if not listing_path:
            continue
        listing_url = urljoin(base_url, str(listing_path))
        if listing_url in seen_urls:
            continue
        seen_urls.add(listing_url)

        location = home.get("location") or {}
        if not isinstance(location, dict):
            location = {}
        line = location.get("street") or location.get("address") or ""
        city = location.get("city") or ""
        state = location.get("state") or ""
        title = ", ".join(part for part in (line, city, state) if part) or "Trulia rental"

        lat = location.get("latitude") or location.get("lat")
        lng = location.get("longitude") or location.get("lng")
        rent = _rent_from_home(home)

        results.append(
            {
                "title": str(title)[:200],
                "url": listing_url,
                "rent": rent,
                "bedrooms": home.get("bedrooms"),
                "bathrooms": home.get("bathrooms"),
                "snippet": "Via Trulia (Zillow network).",
                "photos": _photo_from_home(home),
                "listing_address": title,
                "latitude": float(lat) if lat is not None else None,
                "longitude": float(lng) if lng is not None else None,
            }
        )
    return results[:24]


def fetch_trulia_search_html(parsed: ParsedLocation, timeout: float = 25.0) -> tuple[str, str, Optional[str]]:
    from curl_cffi import requests as curl_requests

    url = _trulia_search_url(parsed)
    try:
        response = curl_requests.get(
            url,
            headers=TRULIA_HEADERS,
            timeout=timeout,
            allow_redirects=True,
            impersonate="safari17_0",
        )
        if response.status_code >= 400:
            return "", url, f"Trulia returned {response.status_code}"
        if len(response.text) < 5000:
            return "", url, "Trulia returned a blocked or empty page"
        return response.text, str(response.url), None
    except ImportError:
        return "", url, "Trulia search requires curl_cffi"
    except Exception as exc:
        return "", url, str(exc)

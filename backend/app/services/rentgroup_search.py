"""Parse Rent.com / ApartmentGuide search pages (shared __NEXT_DATA__ format)."""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list, rent_com_photo_url
from app.services.profile_requirements import expand_bedroom_range

RENT_LC_ID_RE = re.compile(r"-lc(\d+)", re.I)


def build_rent_com_listing_url(listing: dict, base_url: str = "https://www.rent.com") -> str:
    path = listing.get("urlPathname") or ""
    if path.startswith("/apartment/"):
        return urljoin(base_url, path)
    listing_id = str(listing.get("id") or "")
    if listing_id.startswith("lc"):
        slug = re.sub(r"[^a-z0-9]+", "-", str(listing.get("name") or "listing").lower()).strip("-")
        city = (listing.get("location") or {}).get("city", "city")
        state = (listing.get("location") or {}).get("stateAbbr", "st").lower()
        return urljoin(base_url, f"/apartment/{slug}-{city.lower()}-{state.lower()}-{listing_id}")
    return ""


def build_apartmentguide_listing_url(
    listing: dict, base_url: str = "https://www.apartmentguide.com"
) -> str:
    path = listing.get("urlPathname") or ""
    if path.startswith("/a/"):
        return urljoin(base_url, path)
    return ""


def _sanitize_apartments_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return re.sub(r"-+", "-", slug)


def _slug_from_ag_pathname(pathname: str) -> str:
    match = re.match(r"/a/([^/]+)/?", pathname, re.I)
    if not match:
        return ""
    body = match.group(1)
    body = re.sub(r"-[a-z]{2}-\d+$", "", body, flags=re.I)
    return _sanitize_apartments_slug(body)


def build_apartments_com_listing_url(listing: dict) -> Optional[str]:
    """Map RentGroup listing metadata to apartments.com detail URLs."""
    source_id = str(listing.get("sourceId") or "").strip()
    if not source_id:
        return None
    pathname = str(listing.get("urlPathname") or "")

    apt_match = re.match(r"/apartment/(.+)-lc\d+/?$", pathname, re.I)
    if apt_match:
        slug = _sanitize_apartments_slug(apt_match.group(1))
        return f"https://www.apartments.com/{slug}/{source_id}/"

    if pathname.startswith("/a/"):
        slug = _slug_from_ag_pathname(pathname)
        if slug:
            return f"https://www.apartments.com/{slug}/{source_id}/"

    name = str(listing.get("name") or "listing")
    location = listing.get("location") or {}
    city = str(location.get("city") or "city")
    state = str(location.get("stateAbbr") or "st")
    slug = _sanitize_apartments_slug(f"{name}-{city}-{state}")
    return f"https://www.apartments.com/{slug}/{source_id}/"


def _rent_from_listing(listing: dict, match: Optional[dict] = None) -> Optional[float]:
    if match:
        prices = match.get("prices") or {}
        if isinstance(prices, dict):
            low = prices.get("low")
            if low is not None:
                return float(low)
    price = listing.get("price")
    if price is not None:
        try:
            return float(price)
        except (TypeError, ValueError):
            pass
    bed_data = listing.get("bedCountData") or []
    if bed_data and isinstance(bed_data[0], dict):
        prices = bed_data[0].get("prices") or {}
        low = prices.get("low") if isinstance(prices, dict) else None
        if low is not None:
            return float(low)
    return None


def _bedroom_counts_from_listing(
    listing: dict,
    match: Optional[dict],
) -> set[int]:
    counts: set[int] = set()
    if match:
        beds = match.get("beds") or {}
        if isinstance(beds, dict) and beds.get("low") is not None:
            low = float(beds["low"])
            high = float(beds["high"]) if beds.get("high") is not None else None
            counts.update(expand_bedroom_range(low, high))

    for entry in listing.get("bedCountData") or []:
        if not isinstance(entry, dict):
            continue
        bed_val = entry.get("beds")
        if bed_val is None:
            bed_val = entry.get("bedCount")
        if bed_val is not None:
            counts.add(int(round(float(bed_val))))

    return counts


def _beds_baths_from_match(match: Optional[dict]) -> tuple[Optional[float], Optional[float]]:
    if not match:
        return None, None
    beds = match.get("beds") or {}
    baths = match.get("baths") or {}
    bed_val = beds.get("low") if isinstance(beds, dict) else None
    bath_val = baths.get("low") if isinstance(baths, dict) else None
    return (
        float(bed_val) if bed_val is not None else None,
        float(bath_val) if bath_val is not None else None,
    )


def _photos_from_listing(listing: dict, site: str) -> list[str]:
    photos: list[str] = []
    for photo in listing.get("photos") or []:
        if isinstance(photo, dict) and photo.get("id"):
            photos.append(rent_com_photo_url(str(photo["id"]), "xl"))
        elif isinstance(photo, str):
            photos.append(photo)
    # RentGroup serves images from i.rent.com regardless of surface site
    return normalize_photo_list(photos, "rent.com", limit=5)


def parse_rentgroup_search(
    html: str,
    *,
    site: str,
    listing_url_builder,
    limit: int = 40,
) -> list[dict]:
    """Extract listings from Rent.com / ApartmentGuide search HTML."""
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []

    try:
        data = json.loads(script.string)
        page_location = (
            data.get("props", {})
            .get("pageProps", {})
            .get("pageData", {})
            .get("location", {})
        )
        listing_search = page_location.get("listingSearch") or {}
        matches = listing_search.get("filterMatchResults") or []
        listings = listing_search.get("listings") or []
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []

    listings_by_id = {
        str(item.get("id", "")): item
        for item in listings
        if isinstance(item, dict) and item.get("id")
    }

    results: list[dict] = []
    seen_urls: set[str] = set()

    def append_listing(listing: dict, match: Optional[dict]) -> None:
        listing_url = listing_url_builder(listing)
        if not listing_url or listing_url in seen_urls:
            return
        seen_urls.add(listing_url)

        location_meta = listing.get("location") or {}
        latitude = location_meta.get("lat")
        longitude = location_meta.get("lng")
        listing_address = listing.get("addressFull") or listing.get("address") or ""

        beds, baths = _beds_baths_from_match(match)
        bedroom_counts = _bedroom_counts_from_listing(listing, match)
        snippet_parts: list[str] = []
        if listing.get("priceText"):
            snippet_parts.append(str(listing["priceText"]))
        elif match and isinstance(match.get("prices"), dict):
            prices = match["prices"]
            low, high = prices.get("low"), prices.get("high")
            if low and high:
                snippet_parts.append(f"${int(low)} – ${int(high)}/mo")
            elif low:
                snippet_parts.append(f"From ${int(low)}/mo")

        if bedroom_counts:
            snippet_parts.append(
                " · ".join(f"{count} bed" for count in sorted(bedroom_counts))
            )
        elif beds is not None:
            snippet_parts.append(f"{beds} bed")
        if baths is not None:
            snippet_parts.append(f"{baths} bath")
        if listing.get("squareFeetText"):
            snippet_parts.append(str(listing["squareFeetText"]))

        results.append(
            {
                "title": str(listing.get("name") or "Rental listing"),
                "url": listing_url,
                "snippet": " · ".join(snippet_parts),
                "photos": _photos_from_listing(listing, site),
                "rent": _rent_from_listing(listing, match),
                "bedrooms": beds,
                "bathrooms": baths,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "listing_address": str(listing_address) if listing_address else "",
                "source_id": listing.get("sourceId"),
                "apartments_com_url": build_apartments_com_listing_url(listing),
                "rent_com_url": build_rent_com_listing_url(listing),
            }
        )

    for match in matches:
        if not isinstance(match, dict):
            continue
        listing_id = str(match.get("listingId") or "")
        listing = listings_by_id.get(listing_id)
        if listing:
            append_listing(listing, match)
        if len(results) >= limit:
            break

    if len(results) < limit:
        for listing in listings:
            if len(results) >= limit:
                break
            if not isinstance(listing, dict):
                continue
            listing_id = str(listing.get("id") or "")
            match = next(
                (m for m in matches if str(m.get("listingId")) == listing_id),
                None,
            )
            append_listing(listing, match if isinstance(match, dict) else None)

    return results[:limit]

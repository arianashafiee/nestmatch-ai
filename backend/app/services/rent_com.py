import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.image_quality import (
    normalize_photo_list,
    rent_com_photo_url,
    upgrade_rent_com_image,
)

RENT_APARTMENT_LINK_RE = re.compile(
    r'href="(/apartment/[^"]+-lc\d+)"',
    re.I,
)
RENT_LC_ID_RE = re.compile(r"-lc(\d+)", re.I)


def _clean_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw)
    return raw.strip() if len(digits) >= 10 else ""


def _parse_ld_json_images(data) -> list[str]:
    photos: list[str] = []
    image = data.get("image")
    if isinstance(image, str):
        image = [image]
    if isinstance(image, list):
        for item in image:
            if isinstance(item, str):
                photos.append(upgrade_rent_com_image(item))
            elif isinstance(item, dict):
                url = item.get("contentUrl") or item.get("url")
                if url:
                    photos.append(upgrade_rent_com_image(str(url)))
    return photos


def _rent_from_prices(prices: dict) -> Optional[float]:
    if not isinstance(prices, dict):
        return None
    low = prices.get("low")
    if low is not None:
        return float(low)
    high = prices.get("high")
    return float(high) if high is not None else None


def _listing_url_from_id(html: str, base_url: str, listing_id: str) -> str:
    match = re.search(
        rf'href="(/apartment/[^"]*{re.escape(listing_id)})"',
        html,
        re.I,
    )
    if match:
        return urljoin(base_url, match.group(1))
    return ""


def _parse_next_data_search(html: str, base_url: str) -> list[dict]:
    """Primary path: Rent.com embeds search cards in __NEXT_DATA__."""
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
        search = page_location.get("listingSearch", {}).get(
            "filterMatchResults", []
        )
        listings_by_id = {
            str(item.get("id", "")): item
            for item in page_location.get("listingSearch", {}).get("listings", [])
            if isinstance(item, dict) and item.get("id")
        }
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []

    results: list[dict] = []
    seen_urls: set[str] = set()
    for item in search:
        if not isinstance(item, dict):
            continue
        listing_id = str(item.get("listingId", ""))
        if not listing_id:
            continue
        listing_url = _listing_url_from_id(html, base_url, listing_id)
        if not listing_url or listing_url in seen_urls:
            continue
        seen_urls.add(listing_url)

        listing_meta = listings_by_id.get(listing_id, {})
        location_meta = listing_meta.get("location") or {}
        latitude = location_meta.get("lat")
        longitude = location_meta.get("lng")
        listing_address = listing_meta.get("addressFull") or listing_meta.get("address")

        prices = item.get("prices", {})
        snippet_parts = []
        if isinstance(prices, dict):
            low = prices.get("low")
            high = prices.get("high")
            if low and high:
                snippet_parts.append(f"${int(low)} – ${int(high)}/mo")
            elif low:
                snippet_parts.append(f"From ${int(low)}/mo")

        beds = item.get("beds", {})
        baths = item.get("baths", {})
        if isinstance(beds, dict) and beds.get("low") is not None:
            snippet_parts.append(
                f"{beds.get('low', '?')}–{beds.get('high', '?')} bed"
            )
        if isinstance(baths, dict) and baths.get("low") is not None:
            snippet_parts.append(
                f"{baths.get('low', '?')}–{baths.get('high', '?')} bath"
            )

        photos: list[str] = []
        chunk = html[html.find(listing_id) : html.find(listing_id) + 5000]
        ld_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            chunk,
            re.S,
        )
        if ld_match:
            try:
                ld = json.loads(ld_match.group(1))
                photos = normalize_photo_list(
                    _parse_ld_json_images(ld), "rent.com", limit=5
                )
            except (json.JSONDecodeError, TypeError):
                pass

        results.append(
            {
                "title": str(item.get("name") or listing_meta.get("name") or "Rent.com listing"),
                "url": listing_url,
                "snippet": " · ".join(snippet_parts),
                "photos": photos,
                "rent": _rent_from_prices(prices if isinstance(prices, dict) else {}),
                "bedrooms": beds.get("low") if isinstance(beds, dict) else None,
                "bathrooms": baths.get("low") if isinstance(baths, dict) else None,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "listing_address": str(listing_address) if listing_address else "",
            }
        )
    return results


def parse_rent_com_search(html: str, base_url: str) -> list[dict]:
    """Parse rent.com search results from embedded JSON-LD and listing links."""
    next_results = _parse_next_data_search(html, base_url)
    if next_results:
        return next_results[:12]

    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen_urls: set[str] = set()

    # Map listing slug -> metadata from __NEXT_DATA__
    next_data_by_id: dict[str, dict] = {}
    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        try:
            next_data = json.loads(next_script.string)
            page_data = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("pageData", {})
            )
            search = (
                page_data.get("location", {})
                .get("listingSearch", {})
                .get("filterMatchResults", [])
            )
            for item in search:
                listing_id = str(item.get("listingId", "")).lower()
                if listing_id:
                    next_data_by_id[listing_id] = item
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") not in (
                "ApartmentComplex",
                "Residence",
                "Product",
                "Apartment",
            ):
                continue
            name = str(item.get("name", "")).strip()
            photos = normalize_photo_list(
                _parse_ld_json_images(item), "rent.com", limit=5
            )
            url = item.get("url") or ""
            if isinstance(url, list):
                url = url[0] if url else ""
            if not url or "/apartment/" not in str(url):
                # Try to pair with nearest apartment link in parent card
                continue
            listing_url = urljoin(base_url, str(url))
            if listing_url in seen_urls:
                continue
            seen_urls.add(listing_url)

            lc_match = RENT_LC_ID_RE.search(listing_url)
            meta = (
                next_data_by_id.get(f"lc{lc_match.group(1)}", {})
                if lc_match
                else {}
            )
            prices = meta.get("prices", {})
            snippet_parts = []
            if prices:
                low = prices.get("low")
                high = prices.get("high")
                if low and high:
                    snippet_parts.append(f"${int(low)} – ${int(high)}/mo")
                elif low:
                    snippet_parts.append(f"From ${int(low)}/mo")
            beds = meta.get("beds", {})
            baths = meta.get("baths", {})
            if beds:
                snippet_parts.append(
                    f"{beds.get('low', '?')}–{beds.get('high', '?')} bed"
                )
            if baths:
                snippet_parts.append(
                    f"{baths.get('low', '?')}–{baths.get('high', '?')} bath"
                )

            results.append(
                {
                    "title": name or meta.get("name", "Rent.com listing"),
                    "url": listing_url,
                    "snippet": " · ".join(snippet_parts),
                    "photos": photos,
                    "rent": _rent_from_prices(prices),
                    "bedrooms": beds.get("low") if isinstance(beds, dict) else None,
                    "bathrooms": baths.get("low") if isinstance(baths, dict) else None,
                }
            )

    if len(results) < 3:
        for match in RENT_APARTMENT_LINK_RE.finditer(html):
            href = match.group(1)
            listing_url = urljoin(base_url, href)
            if listing_url in seen_urls:
                continue
            seen_urls.add(listing_url)
            chunk = html[match.start() : match.start() + 4000]
            title = (
                href.rstrip("/")
                .split("/")[-1]
                .replace("-", " ")
                .rsplit(" lc", 1)[0]
                .title()
            )
            photos: list[str] = []
            ld_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                chunk,
                re.S,
            )
            if ld_match:
                try:
                    ld = json.loads(ld_match.group(1))
                    photos = normalize_photo_list(
                        _parse_ld_json_images(ld), "rent.com", limit=5
                    )
                    if ld.get("name"):
                        title = str(ld["name"])
                except (json.JSONDecodeError, TypeError):
                    pass

            lc_match = RENT_LC_ID_RE.search(listing_url)
            meta = (
                next_data_by_id.get(f"lc{lc_match.group(1)}", {})
                if lc_match
                else {}
            )
            results.append(
                {
                    "title": meta.get("name", title),
                    "url": listing_url,
                    "snippet": "",
                    "photos": photos,
                    "rent": _rent_from_prices(meta.get("prices", {})),
                    "bedrooms": (meta.get("beds") or {}).get("low"),
                    "bathrooms": (meta.get("baths") or {}).get("low"),
                }
            )

    return results[:12]


def parse_rent_com_listing(html: str, url: str) -> dict:
    """Parse a single rent.com listing detail page."""
    out: dict = {
        "title": "",
        "photos": [],
        "phone": "",
        "email": "",
        "contact_name": "",
        "contact_url": url,
        "description": "",
        "address": "",
    }

    soup = BeautifulSoup(html, "lxml")
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        out["title"] = og_title["content"]

    next_script = soup.find("script", id="__NEXT_DATA__")
    if not next_script or not next_script.string:
        return out

    try:
        next_data = json.loads(next_script.string)
        listing = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("pageData", {})
            .get("listing", {})
        )
    except (json.JSONDecodeError, TypeError, AttributeError):
        return out

    if not isinstance(listing, dict):
        return out

    if listing.get("name"):
        out["title"] = str(listing["name"])
    if listing.get("description"):
        out["description"] = str(listing["description"])[:4000]

    address = listing.get("addressFull") or listing.get("address")
    if isinstance(address, dict):
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("postalCode"),
        ]
        out["address"] = ", ".join(p for p in parts if p)
    elif address:
        out["address"] = str(address)

    for phone_key in (
        "phoneDesktop",
        "phoneMobile",
        "mitsPhone",
        "phoneDesktopText",
        "phoneMobileText",
    ):
        phone = listing.get(phone_key)
        if phone:
            cleaned = _clean_phone(str(phone))
            if cleaned:
                out["phone"] = cleaned
                break

    pmc = listing.get("propertyManagementCompany")
    if isinstance(pmc, dict) and pmc.get("name"):
        out["contact_name"] = str(pmc["name"])

    photo_urls: list[str] = []
    for photo in listing.get("photos") or []:
        if isinstance(photo, dict) and photo.get("id"):
            photo_urls.append(rent_com_photo_url(str(photo["id"]), "xl"))
        elif isinstance(photo, str):
            photo_urls.append(upgrade_rent_com_image(photo))

    # Gallery images embedded in page HTML (higher res than search cards)
    for match in re.findall(r"https://i\.rent\.com/[^\s\"'<>]+", html):
        photo_urls.append(upgrade_rent_com_image(match))

    out["photos"] = normalize_photo_list(photo_urls, "rent.com", limit=25)
    return out

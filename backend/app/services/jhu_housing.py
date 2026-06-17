"""Johns Hopkins off-campus housing portal (offcampushousing.jhu.edu)."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list

JHU_HOUSING_BASE = "https://offcampushousing.jhu.edu"
JHU_HOUSING_SEARCH_URL = f"{JHU_HOUSING_BASE}/housing"


_OFFCAMPUS_IMG_URL_RE = re.compile(
    r"https://img\.offcampusimages\.com/[^\s\"'<>]+",
    re.I,
)
_OFFCAMPUS_IMG_PROTO_RE = re.compile(
    r"//img\.offcampusimages\.com/[^\s\"'<>]+",
    re.I,
)
_BACKGROUND_IMAGE_RE = re.compile(
    r"background-image:\s*url\([\"']?(//img\.offcampusimages\.com/[^)\"']+)[\"']?\)",
    re.I,
)

_GEO_BLOCK_RE = re.compile(
    r"streetAddress&q;:&q;([^&]+)&q;,"
    r"&q;cityName&q;:&q;([^&]+)&q;,"
    r"&q;stateCode&q;:&q;([^&]+)&q;,"
    r"&q;zipCode&q;:&q;([^&]+)&q;,"
    r"&q;latitude&q;:([\d.-]+),"
    r"&q;longitude&q;:([\d.-]+)"
    r"(?:,&q;targetCollege&q;:\{&q;id&q;:&q;\d+&q;,"
    r"&q;name&q;:&q;[^&]+&q;,"
    r"&q;distance&q;:([\d.]+))?",
    re.S,
)

_RENT_RANGE_RE = re.compile(r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?")
_BED_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*bed",
    re.I,
)
_BEDROOM_COUNT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:bedroom|bedrooms|beds|bd)\b",
    re.I,
)
_BATH_COUNT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:bathroom|bathrooms|baths|ba)\b",
    re.I,
)
_LEASE_RE = re.compile(
    r"(\d+\s*(?:month|year|week)s?\s+lease)",
    re.I,
)

PROPERTY_PATH_RE = re.compile(
    r"/housing/property/([^/]+)/([a-z0-9]+)",
    re.I,
)


def _normalize_image_url(url: str) -> str:
    cleaned = url.strip().strip("\"'")
    if cleaned.startswith("//"):
        return "https:" + cleaned
    return cleaned


def is_jhu_placeholder_image(url: str) -> bool:
    lower = url.lower()
    return "cdn.offcampusimages.com" in lower and lower.endswith(".svg")


def _property_id_from_url(url: str) -> str:
    match = PROPERTY_PATH_RE.search(urlparse(url).path)
    return match.group(2) if match else ""


def _extract_offcampus_image_urls(
    html: str,
    soup: Optional[BeautifulSoup] = None,
    *,
    html_scan: bool = False,
) -> list[str]:
    photos: list[str] = []
    if soup is not None:
        for el in soup.select('[data-qaid="image"]'):
            style = el.get("style") or ""
            match = _BACKGROUND_IMAGE_RE.search(style)
            if not match:
                inline = re.search(
                    r"url\([\"']?(//img\.offcampusimages\.com/[^)\"']+)[\"']?\)",
                    style,
                    re.I,
                )
                if inline:
                    match = inline
            if match:
                photos.append(_normalize_image_url(match.group(1)))

    if html_scan:
        for match in _OFFCAMPUS_IMG_PROTO_RE.findall(html):
            photos.append(_normalize_image_url(match))
        for match in _OFFCAMPUS_IMG_URL_RE.findall(html):
            photos.append(_normalize_image_url(match))
    return photos


def _extract_photo_for_property_id(html: str, property_id: str) -> str:
    if not property_id:
        return ""
    idx = html.find(property_id)
    if idx == -1:
        return ""
    chunk = html[idx : idx + 5000]
    for pattern in (_OFFCAMPUS_IMG_PROTO_RE, _OFFCAMPUS_IMG_URL_RE):
        match = pattern.search(chunk)
        if match:
            url = _normalize_image_url(match.group(0))
            if not is_jhu_placeholder_image(url):
                return url
    return ""


def _dedupe_photo_urls(photos: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for photo in photos:
        if not photo or is_jhu_placeholder_image(photo):
            continue
        if photo in seen:
            continue
        seen.add(photo)
        unique.append(photo)
    return unique


def is_jhu_housing_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "offcampushousing.jhu.edu" in host


def fetch_jhu_housing_html(url: str, timeout: float = 25.0) -> tuple[str, str]:
    """Fetch a JHU housing page (Akamai blocks plain httpx)."""
    from curl_cffi import requests as curl_requests

    response = curl_requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        impersonate="chrome131",
        headers={
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": JHU_HOUSING_SEARCH_URL,
        },
    )
    response.raise_for_status()
    return response.text, str(response.url)


def _decode_ocp_json(text: str) -> str:
    return (
        text.replace("&q;", '"')
        .replace("&a;", "&")
        .replace("&s;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def _format_address(street: str, city: str, state: str, zip_code: str) -> str:
    parts = [street.strip(), f"{city.strip()}, {state.strip()} {zip_code.strip()}".strip()]
    return ", ".join(p for p in parts if p)


def _normalize_address_key(address: str) -> str:
    return re.sub(r"\s+", " ", address.lower().replace(",", " ")).strip()


def _parse_rent(text: str) -> Optional[float]:
    if not text:
        return None
    lower = text.lower()
    total_match = re.search(
        r"total monthly price\s*\$?\s*([\d,]+(?:\.\d{2})?)",
        lower,
    )
    if total_match:
        return float(total_match.group(1).replace(",", ""))
    amounts = [
        float(n.replace(",", ""))
        for n in re.findall(r"\$([\d,]+(?:\.\d{2})?)", text)
    ]
    return min(amounts) if amounts else None


def _parse_bedrooms(text: str) -> Optional[float]:
    if not text:
        return None
    lower = text.lower()
    if "studio" in lower:
        return 0.0
    match = _BED_RANGE_RE.search(lower)
    if match:
        return float(match.group(1))
    match = _BEDROOM_COUNT_RE.search(lower)
    if match:
        return float(match.group(1))
    return None


def _parse_bathrooms(text: str) -> Optional[float]:
    if not text:
        return None
    match = _BATH_COUNT_RE.search(text.lower())
    if match:
        return float(match.group(1))
    return None


def _parse_lease_length(text: str) -> Optional[str]:
    if not text:
        return None
    match = _LEASE_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def _text_from_qaid(scope, qaid: str) -> str:
    el = scope.select_one(f'[data-qaid="{qaid}"]')
    return el.get_text(" ", strip=True) if el else ""


HOMewood_CAMPUS_QUERY = "Johns Hopkins University Homewood Campus, Baltimore, MD"


def _parse_drive_time_minutes(text: str) -> Optional[int]:
    match = re.search(r"drive:\s*(\d+)\s*min", text, re.I)
    return int(match.group(1)) if match else None


def _parse_homewood_distance_miles(text: str) -> Optional[float]:
    match = re.search(
        r"([\d.]+)\s*miles?\s+to\s+johns hopkins homewood campus",
        text,
        re.I,
    )
    return float(match.group(1)) if match else None


def _haversine_to_homewood(lat: float, lng: float) -> Optional[float]:
    from app.services.geo import geocode, haversine_miles

    campus = geocode(HOMewood_CAMPUS_QUERY)
    if not campus:
        return None
    return haversine_miles(campus[0], campus[1], lat, lng)


def enrich_jhu_homewood_commute(data: dict, soup: Optional[BeautifulSoup] = None) -> dict:
    """Fill distance_miles from Homewood campus (commute minutes use profile mode later)."""
    distance = data.get("distance_miles")

    if soup is not None:
        dist_text = _text_from_qaid(soup, "multiCampusDistances")
        portal_distance = _parse_homewood_distance_miles(dist_text)
        if portal_distance is not None:
            distance = portal_distance

    lat = data.get("latitude")
    lng = data.get("longitude")
    if distance is None and lat is not None and lng is not None:
        computed = _haversine_to_homewood(float(lat), float(lng))
        if computed is not None:
            distance = computed

    if distance is not None:
        data["distance_miles"] = round(float(distance), 2)
    return data


def compute_homewood_commute_minutes(
    distance_miles: float, commute_mode: str = "walking"
) -> int:
    from app.services.geo import estimate_commute_minutes

    return estimate_commute_minutes(float(distance_miles), commute_mode or "walking")


def extract_jhu_homewood_distance_from_text(text: str) -> Optional[float]:
    match = re.search(
        r"Distance from Homewood campus:\s*([\d.]+)\s*mi",
        text,
        re.I,
    )
    return float(match.group(1)) if match else None


def jhu_commute_line(distance_miles: float, commute_mode: str) -> str:
    minutes = compute_homewood_commute_minutes(distance_miles, commute_mode)
    return f"Commute to Homewood ({commute_mode}): {minutes} min"


def append_jhu_commute_to_listing_text(text: str, commute_mode: str) -> str:
    distance = extract_jhu_homewood_distance_from_text(text)
    if distance is None:
        return text
    line = jhu_commute_line(distance, commute_mode)
    if line in text:
        return text
    return f"{text.rstrip()}\n\n{line}"


def apply_jhu_commute_to_analysis(analysis, listing_text: str, profile) -> object:
    """Set analysis commute from Homewood distance using the student's commute mode."""
    distance = extract_jhu_homewood_distance_from_text(listing_text)
    if distance is None:
        return analysis

    commute_mode = profile.commute_mode or "walking"
    commute_min = compute_homewood_commute_minutes(distance, commute_mode)
    analysis.estimated_commute_minutes = commute_min
    max_commute = profile.max_commute_minutes or 30
    if commute_min <= max_commute:
        commute_score = max(60, int(100 - commute_min))
    else:
        commute_score = max(20, int(60 - (commute_min - max_commute) * 2))
    analysis.score_breakdown.commute = commute_score

    breakdown = analysis.score_breakdown
    analysis.compatibility_score = int(
        breakdown.affordability * 0.3
        + breakdown.commute * 0.25
        + breakdown.amenities * 0.2
        + breakdown.safety_comfort * 0.15
        + breakdown.student_fit * 0.1
    )

    pros = [p for p in analysis.pros if "commute" not in p.lower() and "homewood" not in p.lower()]
    cons = [c for c in analysis.cons if "commute" not in c.lower() and "homewood" not in c.lower()]
    if commute_min <= max_commute:
        pros.append(
            f"{commute_min} min {commute_mode} to Homewood fits your {max_commute} min limit"
        )
    else:
        cons.append(
            f"{commute_min} min {commute_mode} to Homewood exceeds your {max_commute} min limit"
        )
    analysis.pros = pros[:4] if pros else analysis.pros
    analysis.cons = cons[:4] if cons else analysis.cons
    return analysis


def format_jhu_listing_details(parsed: dict) -> str:
    """Structured lines for listing raw_text / analysis."""
    lines: list[str] = []
    if parsed.get("address"):
        lines.append(f"Address: {parsed['address']}")
    if parsed.get("rent"):
        lines.append(f"Rent: ${int(parsed['rent']):,}/mo")
    elif parsed.get("rent_formatted"):
        lines.append(f"Rent: {parsed['rent_formatted']}/mo")
    if parsed.get("bedrooms") is not None:
        bed_label = "Studio" if parsed["bedrooms"] == 0 else f"{int(parsed['bedrooms'])} bed"
        if parsed.get("bathrooms") is not None:
            lines.append(f"Beds/Baths: {bed_label} / {int(parsed['bathrooms'])} bath")
        else:
            lines.append(f"Beds: {bed_label}")
    elif parsed.get("bathrooms") is not None:
        lines.append(f"Baths: {parsed['bathrooms']} bath")
    if parsed.get("lease_length"):
        lines.append(f"Lease length: {parsed['lease_length']}")
    if parsed.get("availability"):
        lines.append(f"Availability: {parsed['availability']}")
    if parsed.get("distance_miles") is not None:
        lines.append(
            f"Distance from Homewood campus: {parsed['distance_miles']} mi"
        )
    return "\n".join(lines)


def _extract_geo_lookup(html: str) -> dict[str, dict]:
    """Map normalized street address -> lat/lng (+ optional campus distance)."""
    lookup: dict[str, dict] = {}
    for match in _GEO_BLOCK_RE.finditer(html):
        street, city, state, zip_code, lat, lng, distance = match.groups()
        address = _format_address(street, city, state, zip_code)
        key = _normalize_address_key(address)
        lookup[key] = {
            "address": address,
            "latitude": float(lat),
            "longitude": float(lng),
            "distance_miles": float(distance) if distance else None,
        }
    return lookup


def _extract_embedded_property(html: str) -> dict:
    decoded = _decode_ocp_json(html)
    out: dict = {}
    street = re.search(r'"streetAddress"\s*:\s*"([^"]+)"', decoded)
    city = re.search(r'"cityName"\s*:\s*"([^"]+)"', decoded)
    state = re.search(r'"stateCode"\s*:\s*"([^"]+)"', decoded)
    zip_code = re.search(r'"zipCode"\s*:\s*"([^"]+)"', decoded)
    lat = re.search(r'"latitude"\s*:\s*([\d.-]+)', decoded)
    lng = re.search(r'"longitude"\s*:\s*([\d.-]+)', decoded)
    distance = re.search(
        r'"targetCollege"\s*:\s*\{[^}]*"distance"\s*:\s*([\d.]+)',
        decoded,
    )
    if street and city and state and zip_code:
        out["address"] = _format_address(
            street.group(1),
            city.group(1),
            state.group(1),
            zip_code.group(1),
        )
    if lat and lng:
        out["latitude"] = float(lat.group(1))
        out["longitude"] = float(lng.group(1))
    if distance:
        out["distance_miles"] = float(distance.group(1))

    beds = re.search(r'"bedrooms"\s*:\s*\{\s*"low"\s*:\s*(\d+(?:\.\d+)?)', decoded)
    baths = re.search(r'"bathrooms"\s*:\s*\{\s*"low"\s*:\s*(\d+(?:\.\d+)?)', decoded)
    price_low = re.search(r'"priceLow"\s*:\s*(\d+)', decoded)
    price_high = re.search(r'"priceHigh"\s*:\s*(\d+)', decoded)
    price_formatted = re.search(
        r'"matching"\s*:\s*\{[^}]*"price"\s*:\s*\{[^}]*"formatted"\s*:\s*"([^"]+)"',
        decoded,
        re.S,
    )
    if beds:
        out["bedrooms"] = float(beds.group(1))
    if baths:
        out["bathrooms"] = float(baths.group(1))
    if price_low:
        out["rent"] = float(price_low.group(1))
        if price_high and price_high.group(1) != price_low.group(1):
            out["rent_high"] = float(price_high.group(1))
    if price_formatted:
        out["rent_formatted"] = price_formatted.group(1)

    return out


def _extract_listing_scope(soup: BeautifulSoup):
    return soup.select_one('[data-qaid="listingSummary"]') or soup


def _extract_floor_plan_text(soup: BeautifulSoup) -> str:
    rows = soup.select('[data-qaid="floorPlanRow"]')
    return " | ".join(row.get_text(" | ", strip=True) for row in rows[:3])


def _extract_photos(soup: BeautifulSoup, html: str) -> list[str]:
    photos = _extract_offcampus_image_urls(html, soup, html_scan=False)

    for img in soup.select("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            src = img.get(attr) or ""
            if "apartments.com" in src and "image.jpg" in src:
                photos.append(_normalize_image_url(src))

    if not photos:
        photos.extend(
            re.findall(
                r"https://images\d*\.apartments\.com/[^\s\"'<>]+/image\.jpg[^\s\"'<>]*",
                html,
                re.I,
            )
        )

    return normalize_photo_list(_dedupe_photo_urls(photos), "jhu_housing", limit=25)


def parse_jhu_housing_listing(html: str, url: str) -> dict:
    """Parse a single JHU off-campus housing property page."""
    soup = BeautifulSoup(html, "lxml")
    embedded = _extract_embedded_property(html)

    title_el = soup.select_one("h1")
    og_title = soup.find("meta", property="og:title")
    title = ""
    if title_el:
        title = title_el.get_text(" ", strip=True)
    elif og_title and og_title.get("content"):
        title = og_title["content"].split("|")[0].strip()

    address = embedded.get("address", "")
    addr_el = soup.select_one('[data-qaid="address"]')
    if addr_el:
        address = addr_el.get_text(" ", strip=True) or address

    phone = ""
    phone_el = soup.select_one('a[href^="tel:"]')
    if phone_el:
        phone = phone_el.get("href", "").replace("tel:", "").strip()
        if not phone:
            phone = phone_el.get_text(" ", strip=True)

    description = ""
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()

    scope = _extract_listing_scope(soup)
    page = soup
    beds_text = _text_from_qaid(page, "beds")
    baths_text = _text_from_qaid(page, "baths")
    price_text = _text_from_qaid(page, "price") or _text_from_qaid(scope, "rangeInfo")
    availability = _text_from_qaid(page, "availability")
    floor_text = _extract_floor_plan_text(soup)
    detail_text = " | ".join(
        part for part in (price_text, beds_text, baths_text, floor_text) if part
    )

    rent = embedded.get("rent") or _parse_rent(detail_text)
    bedrooms = embedded.get("bedrooms")
    if bedrooms is None:
        bedrooms = _parse_bedrooms(beds_text or detail_text)
    bathrooms = embedded.get("bathrooms")
    if bathrooms is None:
        bathrooms = _parse_bathrooms(baths_text or detail_text)
    lease_length = _parse_lease_length(detail_text)

    snippet_parts = [
        p
        for p in (
            embedded.get("rent_formatted") or (f"${int(rent):,}/mo" if rent else ""),
            f"{int(bedrooms)} bed" if bedrooms is not None else "",
            f"{int(bathrooms)} bath" if bathrooms is not None else "",
            lease_length,
            availability,
        )
        if p
    ]

    result = {
        "title": title,
        "photos": _extract_photos(soup, html),
        "phone": phone,
        "email": "",
        "contact_name": "",
        "contact_url": url,
        "description": description,
        "address": address,
        "latitude": embedded.get("latitude"),
        "longitude": embedded.get("longitude"),
        "distance_miles": embedded.get("distance_miles"),
        "rent": rent,
        "rent_formatted": embedded.get("rent_formatted"),
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "lease_length": lease_length,
        "availability": availability,
        "snippet": " · ".join(snippet_parts),
    }
    return enrich_jhu_homewood_commute(result, soup)


def parse_jhu_housing_search(html: str, base_url: str = JHU_HOUSING_SEARCH_URL) -> list[dict]:
    """Parse the JHU housing search page into listing cards."""
    soup = BeautifulSoup(html, "lxml")
    geo_lookup = _extract_geo_lookup(html)
    results: list[dict] = []
    seen_urls: set[str] = set()

    for link in soup.select('a[href*="/housing/property/"]'):
        href = link.get("href", "")
        match = PROPERTY_PATH_RE.search(href)
        if not match:
            continue
        listing_url = urljoin(base_url, href)
        if listing_url in seen_urls:
            continue
        seen_urls.add(listing_url)

        title = link.get_text(" ", strip=True)
        property_id = match.group(2)
        container = link.find_parent("div")
        address = ""
        price_text = ""
        bed_text = ""
        photo = _extract_photo_for_property_id(html, property_id)
        for _ in range(10):
            if container is None:
                break
            if not address:
                addr_el = container.select_one(
                    "address p, .address-container p, [class*='address'] p"
                )
                if addr_el:
                    address = addr_el.get_text(" ", strip=True)
            if not price_text:
                price_el = container.select_one('[data-qaid="price-range"]')
                if price_el:
                    price_text = price_el.get_text(" ", strip=True)
            if not bed_text:
                bed_el = container.select_one('[data-qaid="bed-range"]')
                if bed_el:
                    bed_text = bed_el.get_text(" ", strip=True)
            if not photo:
                for el in container.select('[data-qaid="image"]'):
                    style = el.get("style") or ""
                    bg_match = _BACKGROUND_IMAGE_RE.search(style)
                    if bg_match:
                        photo = _normalize_image_url(bg_match.group(1))
                        break
            if not photo:
                img_el = container.select_one(
                    'img[src*="offcampusimages.com"], img[src*="apartments.com"], '
                    'img[src*="forrent"], img[src*="frmonline"]'
                )
                if img_el:
                    photo = img_el.get("src") or img_el.get("data-src") or ""
            container = container.parent

        geo = geo_lookup.get(_normalize_address_key(address), {})
        if not address and geo.get("address"):
            address = geo["address"]

        photos = (
            normalize_photo_list(_dedupe_photo_urls([photo]), "jhu_housing", limit=5)
            if photo
            else []
        )

        item = {
            "title": title[:200],
            "url": listing_url,
            "listing_address": address,
            "snippet": "",
            "photos": photos,
            "rent": _parse_rent(price_text),
            "bedrooms": _parse_bedrooms(bed_text),
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "distance_miles": geo.get("distance_miles"),
        }
        item = enrich_jhu_homewood_commute(item)
        snippet_parts = [p for p in (price_text, bed_text) if p]
        if item.get("distance_miles") is not None:
            snippet_parts.append(f"{item['distance_miles']} mi from Homewood")
        item["snippet"] = " · ".join(snippet_parts)
        results.append(item)

    return results


def search_jhu_housing(
    parsed, max_rent: float
) -> tuple[list[dict], Optional[str]]:
    """Load listings from the JHU off-campus housing portal."""
    del parsed  # portal is JHU-specific; not filtered by city slug
    try:
        html, final_url = fetch_jhu_housing_html(JHU_HOUSING_SEARCH_URL)
    except Exception as exc:
        return [], f"Could not load JHU off-campus housing: {exc}"

    items = parse_jhu_housing_search(html, final_url)
    if not items:
        return [], "No listings found on JHU off-campus housing"

    if max_rent:
        affordable = [
            item
            for item in items
            if item.get("rent") is None or item["rent"] <= max_rent
        ]
        if affordable:
            items = affordable

    return items[:50], None

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models import StudentProfile
from app.services.geo import (
    estimate_commute_minutes,
    geocode,
    haversine_miles,
    max_commute_radius_miles,
)
from app.services.location_parse import ParsedLocation, parse_campus_location
from app.services.search_fetcher import fetch_search_page

MAX_FETCH_PER_SOURCE = 50
MAX_RESULTS_PER_SOURCE = 24
MAX_TOTAL_RESULTS = 72
COMMUTE_SOFT_FALLBACK_COUNT = 15
APARTMENTGUIDE_SEARCH_PAGES = 5

STATE_SLUGS = {
    "al": "alabama",
    "ak": "alaska",
    "az": "arizona",
    "ar": "arkansas",
    "ca": "california",
    "co": "colorado",
    "ct": "connecticut",
    "de": "delaware",
    "fl": "florida",
    "ga": "georgia",
    "hi": "hawaii",
    "id": "idaho",
    "il": "illinois",
    "in": "indiana",
    "ia": "iowa",
    "ks": "kansas",
    "ky": "kentucky",
    "la": "louisiana",
    "me": "maine",
    "md": "maryland",
    "ma": "massachusetts",
    "mi": "michigan",
    "mn": "minnesota",
    "ms": "mississippi",
    "mo": "missouri",
    "mt": "montana",
    "ne": "nebraska",
    "nv": "nevada",
    "nh": "new-hampshire",
    "nj": "new-jersey",
    "nm": "new-mexico",
    "ny": "new-york",
    "nc": "north-carolina",
    "nd": "north-dakota",
    "oh": "ohio",
    "ok": "oklahoma",
    "or": "oregon",
    "pa": "pennsylvania",
    "ri": "rhode-island",
    "sc": "south-carolina",
    "sd": "south-dakota",
    "tn": "tennessee",
    "tx": "texas",
    "ut": "utah",
    "vt": "vermont",
    "va": "virginia",
    "wa": "washington",
    "wv": "west-virginia",
    "wi": "wisconsin",
    "wy": "wyoming",
    "dc": "district-of-columbia",
}


@dataclass
class SearchResult:
    title: str
    url: str
    source_site: str
    rent: Optional[float] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    snippet: str = ""
    photos: list[str] = field(default_factory=list)
    location: str = ""
    listing_address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_miles: Optional[float] = None
    commute_minutes: Optional[int] = None


def _search_area(parsed: ParsedLocation) -> str:
    if parsed.is_usable_for_search:
        return parsed.city_state
    return parsed.raw


def _slugify_location(parsed: ParsedLocation) -> str:
    if parsed.search_slug:
        return parsed.search_slug
    cleaned = parsed.raw.strip().lower()
    cleaned = re.sub(r"[^\w\s,-]", "", cleaned)
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            city = re.sub(r"\s+", "-", parts[-2])
            state = parts[-1].split()[0][:2]
            return f"{city}-{state}"
    return re.sub(r"\s+", "-", cleaned)


def _craigslist_subdomain(parsed: ParsedLocation) -> str:
    slug = _slugify_location(parsed)
    city = (
        re.sub(r"\s+", "-", parsed.city.lower())
        if parsed.city
        else slug.split("-")[0] if slug else "sfbay"
    )
    mapping = {
        "ann": "annarbor",
        "ann-arbor": "annarbor",
        "austin": "austin",
        "baltimore": "baltimore",
        "boston": "boston",
        "chicago": "chicago",
        "los": "losangeles",
        "new": "newyork",
        "san": "sfbay",
        "seattle": "seattle",
        "denver": "denver",
        "atlanta": "atlanta",
    }
    for key, subdomain in mapping.items():
        if city.startswith(key) or slug.startswith(key):
            return subdomain
    return city or "sfbay"


def _parse_price(text: str) -> Optional[float]:
    match = re.search(r"\$[\d,]+", text)
    if match:
        return float(match.group().replace("$", "").replace(",", ""))
    return None


def _parse_beds_baths(text: str) -> Tuple[Optional[float], Optional[float]]:
    beds = None
    baths = None
    if re.search(r"studio", text, re.I):
        beds = 0
    bed_match = re.search(r"(\d+)\s*(?:br|bed|bd)", text, re.I)
    if bed_match:
        beds = float(bed_match.group(1))
    bath_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ba|bath)", text, re.I)
    if bath_match:
        baths = float(bath_match.group(1))
    return beds, baths


def _rent_com_location_path(parsed: ParsedLocation) -> Optional[str]:
    if not parsed.is_usable_for_search:
        return None
    city = re.sub(r"\s+", "-", parsed.city.lower())
    state_slug = STATE_SLUGS.get(parsed.state, parsed.state)
    return f"{state_slug}/{city}"


def _rent_com_search_url(parsed: ParsedLocation, max_rent: float) -> Optional[str]:
    path = _rent_com_location_path(parsed)
    if not path:
        return None
    state, city = path.split("/", 1)
    url = f"https://www.rent.com/{state}/{city}-apartments"
    if max_rent:
        url = f"{url}/max-price-{int(max_rent)}"
    return url


def _realtor_search_url(parsed: ParsedLocation) -> str:
    if parsed.city and parsed.state:
        city_slug = parsed.city.replace(" ", "-")
        return f"https://www.realtor.com/apartments/{city_slug}_{parsed.state.upper()}"
    from app.services.realtor_com import _realtor_location_slug

    return f"https://www.realtor.com/apartments/{_realtor_location_slug(parsed.raw)}"


def _zillow_search_url(parsed: ParsedLocation) -> str:
    slug = _slugify_location(parsed).replace(",", "")
    return f"https://www.zillow.com/{slug}/rentals/"


def _listing_geocode_query(result: SearchResult, parsed: ParsedLocation) -> str:
    if result.listing_address:
        return result.listing_address
    if result.latitude is not None and result.longitude is not None:
        return ""
    if parsed.is_usable_for_search:
        return f"{result.title}, {parsed.city}, {parsed.state.upper()}"
    return f"{result.title}, {result.location}"


def _apply_commute_filter(
    results: list[SearchResult],
    campus_coords: Optional[tuple[float, float]],
    parsed: ParsedLocation,
    commute_mode: str,
    max_commute_minutes: int,
) -> list[SearchResult]:
    if not campus_coords:
        return results

    campus_lat, campus_lng = campus_coords
    scored: list[tuple[int, SearchResult]] = []

    for result in results:
        lat = result.latitude
        lng = result.longitude
        if lat is None or lng is None:
            query = _listing_geocode_query(result, parsed)
            if query:
                coords = geocode(query)
                if coords:
                    lat, lng = coords

        if lat is None or lng is None:
            continue

        distance = haversine_miles(campus_lat, campus_lng, lat, lng)
        commute = estimate_commute_minutes(distance, commute_mode)
        result.latitude = lat
        result.longitude = lng
        result.distance_miles = round(distance, 2)
        result.commute_minutes = commute
        scored.append((commute, result))

    if not scored:
        return []

    scored.sort(key=lambda pair: (pair[0], -(pair[1].rent or 0)))
    strict = [result for commute, result in scored if commute <= max_commute_minutes]
    filtered = list(strict)
    seen_ids = {id(result) for result in filtered}

    if len(filtered) < COMMUTE_SOFT_FALLBACK_COUNT:
        for commute, result in scored:
            if len(filtered) >= COMMUTE_SOFT_FALLBACK_COUNT:
                break
            if id(result) in seen_ids:
                continue
            seen_ids.add(id(result))
            if commute > max_commute_minutes:
                note = (
                    f"~{commute} min {commute_mode} "
                    f"(outside your {max_commute_minutes} min limit)"
                )
                if note not in result.snippet:
                    result.snippet = f"{note}. {result.snippet}".strip()
            filtered.append(result)

    return filtered


def _item_to_search_result(
    item: dict,
    source_site: str,
    area: str,
    *,
    url_key: str = "url",
) -> SearchResult:
    beds = item.get("bedrooms")
    baths = item.get("bathrooms")
    if beds is None or baths is None:
        parsed_beds, parsed_baths = _parse_beds_baths(
            item.get("snippet", "") + " " + item.get("title", "")
        )
        beds = beds if beds is not None else parsed_beds
        baths = baths if baths is not None else parsed_baths
    return SearchResult(
        title=item.get("title", f"{source_site} listing"),
        url=item[url_key],
        source_site=source_site,
        rent=item.get("rent"),
        bedrooms=beds,
        bathrooms=baths,
        snippet=item.get("snippet", ""),
        photos=item.get("photos", []),
        location=area,
        listing_address=item.get("listing_address", ""),
        latitude=item.get("latitude"),
        longitude=item.get("longitude"),
    )


def search_apartments_com(
    parsed: ParsedLocation, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.apartmentguide_com import (
        apartmentguide_search_url,
        parse_apartmentguide_search,
    )
    from app.services.apartments_com import parse_apartments_com_search

    slug = _slugify_location(parsed)
    if not slug and not parsed.is_usable_for_search:
        return [], "Could not parse city/state from campus location"

    area = _search_area(parsed)
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    fetch_note: Optional[str] = None

    if slug:
        url = f"https://www.apartments.com/{slug}/"
        if max_rent:
            url = f"https://www.apartments.com/{slug}/under-{int(max_rent)}/"
        fetched = fetch_search_page(url, site="apartments.com")
        if fetched.ok:
            for item in parse_apartments_com_search(fetched.html, fetched.url):
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])
                results.append(_item_to_search_result(item, "apartments.com", area))
        elif fetched.error:
            fetch_note = fetched.error

    ag_base = apartmentguide_search_url(parsed, max_rent)
    if ag_base:
        for page in range(1, APARTMENTGUIDE_SEARCH_PAGES + 1):
            page_url = ag_base if page == 1 else f"{ag_base.rstrip('/')}/page-{page}/"
            fetched = fetch_search_page(page_url, site="apartmentguide")
            if not fetched.ok:
                break
            page_items = parse_apartmentguide_search(fetched.html, fetched.url)
            if not page_items:
                break
            for item in page_items:
                listing_url = item.get("apartments_com_url") or item["url"]
                if listing_url in seen_urls:
                    continue
                seen_urls.add(listing_url)
                item = dict(item)
                item["url"] = listing_url
                if fetch_note and "ApartmentGuide" not in item.get("snippet", ""):
                    item["snippet"] = (
                        f"Via ApartmentGuide catalog. {item.get('snippet', '')}".strip()
                    )
                results.append(_item_to_search_result(item, "apartments.com", area))
            if page > 1 and len(page_items) < 20:
                break

    if not results:
        return [], fetch_note or "No apartments.com listings found for this area"
    if fetch_note and results:
        return results, f"Direct apartments.com blocked — loaded {len(results)} via ApartmentGuide feed"
    return results, None


def search_rent_com(
    parsed: ParsedLocation, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.apartmentguide_com import (
        apartmentguide_search_url,
        parse_apartmentguide_search,
    )
    from app.services.rent_com import parse_rent_com_search

    url = _rent_com_search_url(parsed, max_rent)
    if not url and not parsed.is_usable_for_search:
        return [], "Could not parse city/state from campus location"

    area = _search_area(parsed)
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    fetch_note: Optional[str] = None

    if url:
        fetched = fetch_search_page(url, site="rent.com")
        if fetched.ok:
            for item in parse_rent_com_search(fetched.html, fetched.url):
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])
                results.append(_item_to_search_result(item, "rent.com", area))
        elif fetched.error:
            fetch_note = fetched.error

    ag_base = apartmentguide_search_url(parsed, max_rent)
    if ag_base:
        for page in range(1, APARTMENTGUIDE_SEARCH_PAGES + 1):
            page_url = ag_base if page == 1 else f"{ag_base.rstrip('/')}/page-{page}/"
            fetched = fetch_search_page(page_url, site="apartmentguide")
            if not fetched.ok:
                break
            page_items = parse_apartmentguide_search(fetched.html, fetched.url)
            if not page_items:
                break
            for item in page_items:
                listing_url = item.get("rent_com_url") or ""
                if not listing_url or listing_url in seen_urls:
                    continue
                seen_urls.add(listing_url)
                item = dict(item)
                item["url"] = listing_url
                if fetch_note and "ApartmentGuide" not in item.get("snippet", ""):
                    item["snippet"] = (
                        f"Via ApartmentGuide catalog. {item.get('snippet', '')}".strip()
                    )
                results.append(_item_to_search_result(item, "rent.com", area))
            if page > 1 and len(page_items) < 20:
                break

    if not results:
        return [], fetch_note or "No rent.com listings found for this area"
    if fetch_note and results:
        return (
            results,
            f"Direct rent.com limited — loaded {len(results)} via ApartmentGuide feed",
        )
    return results, None


def search_zillow(
    parsed: ParsedLocation, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.zillow_com import parse_zillow_search

    search_url = _zillow_search_url(parsed)
    fetched = fetch_search_page(search_url, site="zillow.com")
    if not fetched.ok:
        return [], fetched.error

    area = _search_area(parsed)
    results: list[SearchResult] = []
    for item in parse_zillow_search(fetched.html, fetched.url):
        if max_rent and item.get("rent") and item["rent"] > max_rent:
            continue
        beds = item.get("bedrooms")
        baths = item.get("bathrooms")
        if beds is None or baths is None:
            parsed_beds, parsed_baths = _parse_beds_baths(
                item.get("snippet", "") + " " + item.get("title", "")
            )
            beds = beds if beds is not None else parsed_beds
            baths = baths if baths is not None else parsed_baths
        results.append(
            SearchResult(
                title=item.get("title", "Zillow rental"),
                url=item["url"],
                source_site="zillow.com",
                rent=item.get("rent"),
                bedrooms=beds,
                bathrooms=baths,
                snippet=item.get("snippet", ""),
                photos=item.get("photos", []),
                location=area,
            )
        )
    if not results:
        return [], "No zillow.com listings parsed (site may block automated search)"
    return results, None


def search_craigslist(
    parsed: ParsedLocation,
    max_rent: float,
    *,
    max_commute_minutes: int = 30,
    commute_mode: str = "walking",
) -> tuple[list[SearchResult], Optional[str]]:
    subdomain = _craigslist_subdomain(parsed)
    url = f"https://{subdomain}.craigslist.org/search/apa"
    params: dict[str, str] = {}
    if max_rent:
        params["max_price"] = str(int(max_rent))
    if parsed.zip_code:
        params["postal"] = parsed.zip_code
        radius = max(1, int(round(max_commute_radius_miles(max_commute_minutes, commute_mode))))
        params["search_distance"] = str(radius)

    fetched = fetch_search_page(url, site="craigslist", params=params)
    if not fetched.ok:
        return [], fetched.error
    soup = BeautifulSoup(fetched.html, "lxml")

    area = _search_area(parsed)
    results: list[SearchResult] = []
    for card in soup.select(
        "li.cl-static-search-result, .result-row, li[data-pid]"
    )[:MAX_FETCH_PER_SOURCE]:
        link = card.select_one("a[href]")
        if not link:
            continue
        listing_url = urljoin(url, link.get("href", ""))
        title = link.get_text(strip=True)
        text = card.get_text(" ", strip=True)
        rent = _parse_price(text)
        beds, baths = _parse_beds_baths(text)
        location_el = card.select_one(".details .location, .location")
        listing_address = location_el.get_text(strip=True) if location_el else ""
        photos = []
        img = card.select_one("img")
        if img and img.get("src", "").startswith("http"):
            photos.append(img["src"])
        if title:
            results.append(
                SearchResult(
                    title=title[:200],
                    url=listing_url,
                    source_site="craigslist",
                    rent=rent,
                    bedrooms=beds,
                    bathrooms=baths,
                    snippet=text[:300],
                    photos=photos,
                    location=area,
                    listing_address=listing_address,
                )
            )

    if results:
        from app.services.craigslist import enrich_craigslist_results_with_cover_photos

        enrich_craigslist_results_with_cover_photos(results)

    if not results:
        return [], "No craigslist listings found for this area"
    return results, None


def search_realtor(
    parsed: ParsedLocation, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.realtor_com import parse_realtor_search

    url = _realtor_search_url(parsed)
    fetched = fetch_search_page(url, site="realtor.com")
    if not fetched.ok:
        return [], fetched.error

    area = _search_area(parsed)
    results: list[SearchResult] = []
    for item in parse_realtor_search(fetched.html, fetched.url):
        if max_rent and item.get("rent") and item["rent"] > max_rent:
            continue
        beds = item.get("bedrooms")
        baths = item.get("bathrooms")
        if beds is None or baths is None:
            parsed_beds, parsed_baths = _parse_beds_baths(
                item.get("snippet", "") + " " + item.get("title", "")
            )
            beds = beds if beds is not None else parsed_beds
            baths = baths if baths is not None else parsed_baths
        results.append(
            SearchResult(
                title=item.get("title", "Realtor.com listing"),
                url=item["url"],
                source_site="realtor.com",
                rent=item.get("rent"),
                bedrooms=beds,
                bathrooms=baths,
                snippet=item.get("snippet", ""),
                photos=item.get("photos", []),
                location=area,
            )
        )
    if not results:
        return [], "No realtor.com listings parsed (site may block automated search)"
    return results, None


def _merge_results_round_robin(
    by_source: dict[str, list[SearchResult]],
    source_order: list[str],
) -> list[SearchResult]:
    merged: list[SearchResult] = []
    seen_urls: set[str] = set()
    max_len = max((len(by_source.get(name, [])) for name in source_order), default=0)

    for index in range(max_len):
        for name in source_order:
            items = by_source.get(name, [])
            if index >= len(items):
                continue
            item = items[index]
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            merged.append(item)
            if len(merged) >= MAX_TOTAL_RESULTS:
                return merged
    return merged


def search_all_sources(profile: StudentProfile) -> dict:
    raw_location = profile.campus_location or profile.university or ""
    parsed = parse_campus_location(raw_location)
    max_rent = profile.max_rent or 2000
    commute_mode = profile.commute_mode or "walking"
    max_commute_minutes = profile.max_commute_minutes or 30

    if not parsed.is_usable_for_search:
        return {
            "results": [],
            "sources_searched": [],
            "errors": {
                "location": (
                    "Could not determine city and state from your campus location. "
                    "Use a full address like 3400 N Charles St, Baltimore, MD or City, ST."
                )
            },
            "location": raw_location,
            "max_rent": max_rent,
            "search_area": "",
            "campus_geocoded": False,
            "max_commute_minutes": max_commute_minutes,
            "commute_mode": commute_mode,
            "ai_ranked": False,
        }

    campus_coords = geocode(parsed.geocode_query)

    sources: list[tuple[str, Callable[..., tuple[list[SearchResult], Optional[str]]]]] = [
        ("apartments.com", search_apartments_com),
        ("rent.com", search_rent_com),
        ("zillow.com", search_zillow),
        ("craigslist", search_craigslist),
        ("realtor.com", search_realtor),
    ]

    by_source: dict[str, list[SearchResult]] = {}
    sources_searched: list[str] = []
    errors: dict[str, str] = {}

    for name, searcher in sources:
        if name == "craigslist":
            results, error = searcher(
                parsed,
                max_rent,
                max_commute_minutes=max_commute_minutes,
                commute_mode=commute_mode,
            )
        else:
            results, error = searcher(parsed, max_rent)
        sources_searched.append(name)
        if error and results:
            errors[name] = error
        elif error and not results:
            errors[name] = error

        filtered = _apply_commute_filter(
            results,
            campus_coords,
            parsed,
            commute_mode,
            max_commute_minutes,
        )
        if campus_coords and results and not filtered:
            errors[name] = (
                f"No listings within {max_commute_minutes} min "
                f"{commute_mode} of campus"
            )
        elif campus_coords and filtered:
            outside = sum(
                1
                for r in filtered
                if r.commute_minutes is not None
                and r.commute_minutes > max_commute_minutes
            )
            if outside:
                commute_note = (
                    f"Including {outside} closest listing(s) outside your "
                    f"{max_commute_minutes} min {commute_mode} limit"
                )
                if name in errors:
                    errors[name] = f"{errors[name]} · {commute_note}"
                else:
                    errors[name] = commute_note

        capped = filtered[:MAX_RESULTS_PER_SOURCE]
        if max_rent:
            capped.sort(
                key=lambda r: (
                    0 if r.rent and r.rent <= max_rent else 1,
                    r.commute_minutes if r.commute_minutes is not None else 999,
                    -(r.rent or 0),
                )
            )
        by_source[name] = capped

    unique = _merge_results_round_robin(by_source, [name for name, _ in sources])

    ai_ranked = False
    if unique:
        from app.config import settings
        from app.services.search_ai import enrich_search_results_with_ai

        if settings.openai_api_key:
            unique, ai_error = enrich_search_results_with_ai(unique, profile)
            if ai_error:
                errors["openai"] = f"AI ranking skipped: {ai_error}"
            else:
                ai_ranked = True

    return {
        "results": unique,
        "sources_searched": sources_searched,
        "errors": errors,
        "location": raw_location,
        "search_area": _search_area(parsed),
        "max_rent": max_rent,
        "campus_geocoded": campus_coords is not None,
        "max_commute_minutes": max_commute_minutes,
        "commute_mode": commute_mode,
        "ai_ranked": ai_ranked,
    }


def search_result_to_raw_text(result: SearchResult) -> str:
    lines = [
        result.title,
        result.url,
        f"Source: {result.source_site}",
        f"Location: {result.location}",
    ]
    if result.listing_address:
        lines.append(f"Address: {result.listing_address}")
    if result.commute_minutes is not None:
        lines.append(f"Estimated commute: {result.commute_minutes} min")
    if result.distance_miles is not None:
        lines.append(f"Distance from campus: {result.distance_miles} mi")
    if result.rent:
        lines.append(f"Rent: ${int(result.rent)}/mo")
    if result.bedrooms is not None:
        lines.append(
            f"Beds/Baths: {result.bedrooms} bed"
            + (f" / {result.bathrooms} bath" if result.bathrooms else "")
        )
    if result.snippet:
        lines.append(result.snippet)
    if result.photos:
        lines.append(f"Photos: {len(result.photos)} image(s) from {result.source_site}")
    return "\n".join(lines)

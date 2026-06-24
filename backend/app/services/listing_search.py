import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models import StudentProfile
from app.services.geo import (
    commute_between_coords,
    geocode,
    max_commute_radius_miles,
)
from app.services.location_parse import ParsedLocation, parse_campus_location
from app.services.profile_requirements import (
    bedroom_requirement_label,
    listing_bedrooms,
    listing_matches_bedroom_requirement,
    listing_within_rent_budget,
    normalize_bedroom_scalar,
    parse_bedroom_counts_from_text,
    rent_per_person_for_profile,
    required_bedrooms,
    occupant_count,
    unit_rent_for_profile,
    unit_rent_budget_limit,
)
from app.services.search_fetcher import fetch_search_page

MAX_FETCH_PER_SOURCE = 50
MAX_RESULTS_PER_SOURCE = 24
MAX_TOTAL_RESULTS = 72
APARTMENTGUIDE_SEARCH_PAGES = 5
MAX_SOURCE_WORKERS = 6

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


@dataclass(frozen=True)
class SearchSource:
    name: str
    search: Callable[[], tuple[list[SearchResult], Optional[str]]]


@dataclass
class SearchSourceResult:
    name: str
    results: list[SearchResult]
    error: Optional[str] = None


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
    counts = parse_bedroom_counts_from_text(text)
    beds = float(max(counts)) if counts else None
    baths = None
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


def _rent_com_search_url(
    parsed: ParsedLocation,
    max_rent: float,
    *,
    min_bedrooms: Optional[int] = None,
) -> Optional[str]:
    path = _rent_com_location_path(parsed)
    if not path:
        return None
    state, city = path.split("/", 1)
    url = f"https://www.rent.com/{state}/{city}-apartments"
    if min_bedrooms and min_bedrooms >= 2:
        url = f"{url}/min-bedrooms-{min_bedrooms}"
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
        return _filter_results_with_known_commute(results, max_commute_minutes)

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

        routed = commute_between_coords(
            campus_lat, campus_lng, lat, lng, commute_mode
        )
        if routed is None:
            continue
        distance, commute = routed
        result.latitude = lat
        result.longitude = lng
        result.distance_miles = round(distance, 2)
        result.commute_minutes = commute
        scored.append((commute, result))

    if not scored:
        return []

    scored.sort(key=lambda pair: (pair[0], -(pair[1].rent or 0)))
    return [result for commute, result in scored if commute <= max_commute_minutes]


def _filter_results_with_known_commute(
    results: list[SearchResult],
    max_commute_minutes: int,
) -> list[SearchResult]:
    """Keep only listings with a computed commute within the user's limit."""
    filtered: list[SearchResult] = []
    for result in results:
        if (
            result.commute_minutes is not None
            and result.commute_minutes <= max_commute_minutes
        ):
            filtered.append(result)
    return filtered


def _apply_bedroom_filter(
    results: list[SearchResult],
    profile: StudentProfile,
) -> list[SearchResult]:
    required = required_bedrooms(profile)
    filtered: list[SearchResult] = []

    for result in results:
        if listing_matches_bedroom_requirement(
            bedrooms=result.bedrooms,
            title=result.title,
            snippet=result.snippet,
            required=required,
        ):
            if result.bedrooms is None:
                parsed = listing_bedrooms(
                    bedrooms=None,
                    title=result.title,
                    snippet=result.snippet,
                )
                if parsed is not None:
                    result.bedrooms = parsed
            filtered.append(result)

    return filtered


def _apply_rent_budget_filter(
    results: list[SearchResult],
    profile: StudentProfile,
) -> list[SearchResult]:
    filtered: list[SearchResult] = []
    for result in results:
        if listing_within_rent_budget(
            result.rent,
            profile,
            title=result.title,
            snippet=result.snippet,
        ):
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
    beds = normalize_bedroom_scalar(beds)
    baths = normalize_bedroom_scalar(baths)
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
    parsed: ParsedLocation,
    max_rent: float,
    *,
    required_beds: Optional[int] = None,
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
        if required_beds and required_beds >= 2:
            url = f"https://www.apartments.com/{slug}/{required_beds}-bedrooms/"
        if max_rent:
            url = (
                f"https://www.apartments.com/{slug}/under-{int(max_rent)}/"
                if not (required_beds and required_beds >= 2)
                else f"https://www.apartments.com/{slug}/{required_beds}-bedrooms/under-{int(max_rent)}/"
            )
        fetched = fetch_search_page(url, site="apartments.com")
        if fetched.ok:
            for item in parse_apartments_com_search(fetched.html, fetched.url):
                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])
                results.append(_item_to_search_result(item, "apartments.com", area))
        elif fetched.error:
            fetch_note = fetched.error

    ag_base = apartmentguide_search_url(
        parsed,
        max_rent,
        min_bedrooms=required_beds if required_beds and required_beds >= 2 else None,
    )
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
    parsed: ParsedLocation,
    max_rent: float,
    *,
    required_beds: Optional[int] = None,
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.apartmentguide_com import (
        apartmentguide_search_url,
        parse_apartmentguide_search,
    )
    from app.services.rent_com import parse_rent_com_search

    url = _rent_com_search_url(
        parsed,
        max_rent,
        min_bedrooms=required_beds if required_beds and required_beds >= 2 else None,
    )
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

    ag_base = apartmentguide_search_url(
        parsed,
        max_rent,
        min_bedrooms=required_beds if required_beds and required_beds >= 2 else None,
    )
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
    from app.services.trulia_com import fetch_trulia_search_html, parse_trulia_search
    from app.services.zillow_com import parse_zillow_search

    search_url = _zillow_search_url(parsed)
    fetched = fetch_search_page(search_url, site="zillow.com")
    fetch_note: Optional[str] = None
    page_items: list[dict] = []

    if fetched.ok:
        page_items = parse_zillow_search(fetched.html, fetched.url)
    else:
        fetch_note = fetched.error

    if not page_items:
        trulia_html, trulia_url, trulia_error = fetch_trulia_search_html(parsed)
        if trulia_html:
            page_items = parse_trulia_search(trulia_html, trulia_url)
            if page_items:
                fetch_note = (
                    f"Direct zillow.com blocked — loaded {len(page_items)} via Trulia feed"
                )
        elif not fetch_note:
            fetch_note = trulia_error or fetched.error

    area = _search_area(parsed)
    results: list[SearchResult] = []
    for item in page_items:
        if max_rent and item.get("rent") and item["rent"] > max_rent:
            continue
        results.append(_item_to_search_result(item, "zillow.com", area))

    if not results:
        return [], fetch_note or "No zillow.com listings found for this area"
    return results, fetch_note


def search_craigslist(
    parsed: ParsedLocation,
    max_rent: float,
    *,
    max_commute_minutes: int = 30,
    commute_mode: str = "walking",
    required_beds: Optional[int] = None,
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
    if required_beds and required_beds >= 2:
        params["min_bedrooms"] = str(required_beds)
        params["query"] = f"{required_beds} bedroom"

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
    from app.services.realtor_search_api import search_realtor_rentals

    area = _search_area(parsed)
    items, error = search_realtor_rentals(parsed, max_rent, limit=MAX_FETCH_PER_SOURCE)
    if error and not items:
        return [], error

    results: list[SearchResult] = []
    for item in items:
        if max_rent and item.get("rent") and item["rent"] > max_rent:
            continue
        results.append(
            _item_to_search_result(item, "realtor.com", area),
        )
    if not results:
        return [], error or "No realtor.com listings found for this area"
    return results, error


def search_jhu_housing(
    parsed: ParsedLocation, max_rent: float, commute_mode: str = "walking"
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.jhu_housing import (
        compute_homewood_commute_minutes,
        search_jhu_housing as load_jhu_listings,
    )

    items, error = load_jhu_listings(parsed, max_rent)
    if not items:
        return [], error or "No JHU off-campus housing listings found"

    results: list[SearchResult] = []
    for item in items:
        distance = item.get("distance_miles")
        commute_min = None
        if distance is not None:
            commute_min = compute_homewood_commute_minutes(float(distance), commute_mode)
        results.append(
            _item_to_search_result(
                item,
                "jhu_housing",
                item.get("listing_address") or "Johns Hopkins off-campus housing",
            )
        )
        last = results[-1]
        if distance is not None:
            last.distance_miles = round(float(distance), 2)
        if commute_min is not None:
            last.commute_minutes = commute_min
    return results, error


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


def _build_search_sources(
    parsed: ParsedLocation,
    unit_rent_limit: float,
    *,
    commute_mode: str,
    max_commute_minutes: int,
    required_beds: int,
) -> list[SearchSource]:
    return [
        SearchSource(
            "jhu_housing",
            lambda: search_jhu_housing(parsed, unit_rent_limit, commute_mode),
        ),
        SearchSource(
            "apartments.com",
            lambda: search_apartments_com(
                parsed,
                unit_rent_limit,
                required_beds=required_beds,
            ),
        ),
        SearchSource(
            "rent.com",
            lambda: search_rent_com(
                parsed,
                unit_rent_limit,
                required_beds=required_beds,
            ),
        ),
        SearchSource(
            "zillow.com",
            lambda: search_zillow(parsed, unit_rent_limit),
        ),
        SearchSource(
            "craigslist",
            lambda: search_craigslist(
                parsed,
                unit_rent_limit,
                max_commute_minutes=max_commute_minutes,
                commute_mode=commute_mode,
                required_beds=required_beds,
            ),
        ),
        SearchSource(
            "realtor.com",
            lambda: search_realtor(parsed, unit_rent_limit),
        ),
    ]


def _sort_source_results(
    results: list[SearchResult],
    profile: StudentProfile,
    max_rent: float,
) -> list[SearchResult]:
    if not max_rent:
        return results
    return sorted(
        results,
        key=lambda r: (
            rent_per_person_for_profile(
                r.rent or 0,
                profile,
                title=r.title,
                snippet=r.snippet,
            )
            if r.rent
            else 999999,
            r.commute_minutes if r.commute_minutes is not None else 999,
        ),
    )


def _run_and_filter_source(
    source: SearchSource,
    *,
    profile: StudentProfile,
    parsed: ParsedLocation,
    campus_coords: Optional[tuple[float, float]],
    commute_mode: str,
    max_commute_minutes: int,
    bedroom_label: str,
    max_rent: float,
) -> SearchSourceResult:
    try:
        results, error = source.search()
    except Exception as exc:
        return SearchSourceResult(source.name, [], str(exc))

    source_error = error
    filtered = _apply_commute_filter(
        results,
        campus_coords,
        parsed,
        commute_mode,
        max_commute_minutes,
    )
    if campus_coords and results and not filtered:
        source_error = (
            f"No listings within {max_commute_minutes} min "
            f"{commute_mode} of campus"
            + (f" from {source.name}" if source.name != "jhu_housing" else "")
        )

    bedroom_filtered = _apply_bedroom_filter(filtered, profile)
    if filtered and not bedroom_filtered:
        source_error = (
            f"No {bedroom_label} listings found"
            + (f" from {source.name}" if source.name != "jhu_housing" else "")
        )
    filtered = bedroom_filtered

    rent_filtered = _apply_rent_budget_filter(filtered, profile)
    if filtered and not rent_filtered:
        source_error = (
            f"No listings within ${int(max_rent)}/mo per person budget"
            + (
                f" (split among {occupant_count(profile)} people)"
                if occupant_count(profile) > 1
                else ""
            )
            + (f" from {source.name}" if source.name != "jhu_housing" else "")
        )
    filtered = rent_filtered

    ranked = _sort_source_results(filtered, profile, max_rent)
    return SearchSourceResult(
        source.name,
        ranked[:MAX_RESULTS_PER_SOURCE],
        source_error,
    )


def _run_sources_concurrently(
    sources: list[SearchSource],
    *,
    profile: StudentProfile,
    parsed: ParsedLocation,
    campus_coords: Optional[tuple[float, float]],
    commute_mode: str,
    max_commute_minutes: int,
    bedroom_label: str,
    max_rent: float,
) -> dict[str, SearchSourceResult]:
    if not sources:
        return {}

    results: dict[str, SearchSourceResult] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_SOURCE_WORKERS, len(sources))) as executor:
        futures = {
            executor.submit(
                _run_and_filter_source,
                source,
                profile=profile,
                parsed=parsed,
                campus_coords=campus_coords,
                commute_mode=commute_mode,
                max_commute_minutes=max_commute_minutes,
                bedroom_label=bedroom_label,
                max_rent=max_rent,
            ): source.name
            for source in sources
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = SearchSourceResult(name, [], str(exc))
    return results


def search_all_sources(profile: StudentProfile) -> dict:
    raw_location = profile.campus_location or profile.university or ""
    parsed = parse_campus_location(raw_location)
    max_rent = profile.max_rent or 2000
    unit_rent_limit = unit_rent_budget_limit(profile)
    commute_mode = profile.commute_mode or "walking"
    max_commute_minutes = profile.max_commute_minutes or 30
    required_beds = required_bedrooms(profile)
    bedroom_label = bedroom_requirement_label(profile)

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
            "ai_discovered": False,
        }

    campus_coords = geocode(parsed.geocode_query)

    sources = _build_search_sources(
        parsed,
        unit_rent_limit,
        commute_mode=commute_mode,
        max_commute_minutes=max_commute_minutes,
        required_beds=required_beds,
    )

    by_source: dict[str, list[SearchResult]] = {}
    errors: dict[str, str] = {}

    source_results = _run_sources_concurrently(
        sources,
        profile=profile,
        parsed=parsed,
        campus_coords=campus_coords,
        commute_mode=commute_mode,
        max_commute_minutes=max_commute_minutes,
        bedroom_label=bedroom_label,
        max_rent=max_rent,
    )
    sources_searched = [source.name for source in sources]
    for source in sources:
        result = source_results.get(source.name, SearchSourceResult(source.name, []))
        if result.error:
            errors[source.name] = result.error
        by_source[source.name] = result.results

    unique = _merge_results_round_robin(by_source, sources_searched)

    from app.services.listing_dedupe import dedupe_cross_site_results

    unique = dedupe_cross_site_results(unique)
    unique = _apply_bedroom_filter(unique, profile)
    unique = _apply_rent_budget_filter(unique, profile)

    ai_discovered = False
    ai_ranked = False
    from app.config import settings

    if settings.openai_api_key:
        from app.services.search_ai import (
            discover_listings_with_ai_web_search,
            enrich_search_results_with_ai,
        )

        ai_results, ai_discover_error = discover_listings_with_ai_web_search(
            profile,
            parsed,
            search_area=_search_area(parsed),
        )
        if ai_discover_error and not ai_results:
            errors["gpt_search"] = ai_discover_error
        elif ai_results:
            ai_commute_filtered = _apply_commute_filter(
                ai_results,
                campus_coords,
                parsed,
                commute_mode,
                max_commute_minutes,
            )
            if campus_coords and ai_results and not ai_commute_filtered:
                errors["gpt_search"] = (
                    f"GPT search found listings but none within "
                    f"{max_commute_minutes} min {commute_mode} of campus"
                )
            ai_bedroom_filtered = _apply_bedroom_filter(ai_commute_filtered, profile)
            if ai_commute_filtered and not ai_bedroom_filtered:
                errors["gpt_search"] = (
                    f"GPT search found listings but none matched {bedroom_label}"
                )
            if ai_bedroom_filtered:
                seen_urls = {item.url for item in unique}
                added = 0
                for item in ai_bedroom_filtered:
                    if item.url in seen_urls:
                        continue
                    seen_urls.add(item.url)
                    unique.append(item)
                    added += 1
                if added:
                    ai_discovered = True
                    if "gpt_search" not in sources_searched:
                        sources_searched.append("gpt_search")

        if unique:
            unique, ai_error = enrich_search_results_with_ai(unique, profile)
            if ai_error:
                errors["openai"] = f"AI ranking skipped: {ai_error}"
            else:
                ai_ranked = True

    unique = _apply_bedroom_filter(unique, profile)
    unique = _apply_rent_budget_filter(unique, profile)
    unique = _apply_commute_filter(
        unique,
        campus_coords,
        parsed,
        commute_mode,
        max_commute_minutes,
    )

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
        "ai_discovered": ai_discovered,
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
    if result.source_site == "jhu_housing" and result.distance_miles is not None:
        lines.append(f"Distance from Homewood campus: {result.distance_miles} mi")
    if result.commute_minutes is not None:
        lines.append(f"Estimated commute: {result.commute_minutes} min")
    if result.distance_miles is not None and result.source_site != "jhu_housing":
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

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from app.models import StudentProfile
from app.services.listing_fetcher import BROWSER_HEADERS, detect_source_site

MAX_RESULTS_PER_SOURCE = 6


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


def _slugify_location(location: str) -> str:
    cleaned = location.strip().lower()
    cleaned = re.sub(r"[^\w\s,-]", "", cleaned)
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            city = re.sub(r"\s+", "-", parts[0])
            state = parts[1].split()[0][:2]
            return f"{city}-{state}"
    return re.sub(r"\s+", "-", cleaned)


def _craigslist_subdomain(location: str) -> str:
    slug = _slugify_location(location)
    city = slug.split("-")[0] if slug else "sfbay"
    mapping = {
        "ann": "annarbor",
        "ann-arbor": "annarbor",
        "austin": "austin",
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
        if slug.startswith(key):
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


def search_apartments_com(
    location: str, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.apartments_com import parse_apartments_com_search

    slug = _slugify_location(location)
    if not slug:
        return [], "Could not parse location for apartments.com"

    url = f"https://www.apartments.com/{slug}/"
    if max_rent:
        url = f"https://www.apartments.com/{slug}/under-{int(max_rent)}/"

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return [], f"apartments.com returned {response.status_code}"
            html = response.text
    except Exception as exc:
        return [], str(exc)

    parsed = parse_apartments_com_search(html, url)
    results: list[SearchResult] = []
    for item in parsed:
        beds, baths = _parse_beds_baths(
            item.get("snippet", "") + " " + item.get("title", "")
        )
        results.append(
            SearchResult(
                title=item.get("title", "Apartments.com listing"),
                url=item["url"],
                source_site="apartments.com",
                rent=item.get("rent"),
                bedrooms=beds,
                bathrooms=baths,
                snippet=item.get("snippet", ""),
                photos=item.get("photos", []),
                location=location,
            )
        )
    if not results:
        return [], "No apartments.com listings parsed (try pasting a direct listing URL)"
    return results, None


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


def _rent_com_location_path(location: str) -> Optional[str]:
    cleaned = location.strip().lower()
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            city = re.sub(r"\s+", "-", parts[0])
            state = parts[1].split()[0][:2]
            state_slug = STATE_SLUGS.get(state, state)
            return f"{state_slug}/{city}"
    slug = _slugify_location(location)
    if "-" in slug:
        city, state = slug.rsplit("-", 1)
        state_slug = STATE_SLUGS.get(state, state)
        return f"{state_slug}/{city}"
    return None


def search_rent_com(
    location: str, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    from app.services.rent_com import parse_rent_com_search

    path = _rent_com_location_path(location)
    if not path:
        return [], "Could not parse location for rent.com (use City, ST format)"

    url = f"https://www.rent.com/{path}/apartments"
    if max_rent:
        url = f"https://www.rent.com/{path}/apartments/under-{int(max_rent)}"

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return [], f"rent.com returned {response.status_code}"
            html = response.text
    except Exception as exc:
        return [], str(exc)

    parsed = parse_rent_com_search(html, url)
    results: list[SearchResult] = []
    for item in parsed:
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
                title=item.get("title", "Rent.com listing"),
                url=item["url"],
                source_site="rent.com",
                rent=item.get("rent"),
                bedrooms=beds,
                bathrooms=baths,
                snippet=item.get("snippet", ""),
                photos=item.get("photos", []),
                location=location,
            )
        )
    if not results:
        return [], "No rent.com listings parsed (try pasting a direct listing URL)"
    return results, None


def search_zillow(location: str, max_rent: float) -> tuple[list[SearchResult], Optional[str]]:
    slug = _slugify_location(location).replace(",", "")
    query = quote_plus(location)
    url = f"https://www.zillow.com/homes/for_rent/?searchQueryState={{}}"
    search_url = (
        f"https://www.zillow.com/homes/for_rent/"
        f"{slug}_rb/?searchQueryState=%7B%22pagination%22%3A%7B%7D%7D"
    )

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            response = client.get(search_url)
            if response.status_code >= 400:
                return [], f"zillow returned {response.status_code}"
            soup = BeautifulSoup(response.text, "lxml")
    except Exception as exc:
        return [], str(exc)

    results: list[SearchResult] = []
    for card in soup.select(
        "article[data-test='property-card'], .property-card, .list-card"
    )[:MAX_RESULTS_PER_SOURCE]:
        link = card.select_one("a[href*='/homedetails/'], a[href*='/b/']")
        if not link:
            continue
        listing_url = urljoin(search_url, link.get("href", ""))
        title = link.get_text(strip=True) or "Zillow rental"
        text = card.get_text(" ", strip=True)
        rent = _parse_price(text)
        beds, baths = _parse_beds_baths(text)
        photos = []
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                photos.append(src)
        results.append(
            SearchResult(
                title=title[:200],
                url=listing_url,
                source_site="zillow.com",
                rent=rent,
                bedrooms=beds,
                bathrooms=baths,
                snippet=text[:300],
                photos=photos,
                location=location,
            )
        )
    return results, None


def search_craigslist(
    location: str, max_rent: float
) -> tuple[list[SearchResult], Optional[str]]:
    subdomain = _craigslist_subdomain(location)
    url = f"https://{subdomain}.craigslist.org/search/apa"
    params = {}
    if max_rent:
        params["max_price"] = str(int(max_rent))

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            response = client.get(url, params=params)
            if response.status_code >= 400:
                return [], f"craigslist returned {response.status_code}"
            soup = BeautifulSoup(response.text, "lxml")
    except Exception as exc:
        return [], str(exc)

    results: list[SearchResult] = []
    for card in soup.select(
        "li.cl-static-search-result, .result-row, li[data-pid]"
    )[:MAX_RESULTS_PER_SOURCE]:
        link = card.select_one("a[href]")
        if not link:
            continue
        listing_url = urljoin(url, link.get("href", ""))
        title = link.get_text(strip=True)
        text = card.get_text(" ", strip=True)
        rent = _parse_price(text)
        beds, baths = _parse_beds_baths(text)
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
                    location=location,
                )
            )
    return results, None


def search_realtor(location: str, max_rent: float) -> tuple[list[SearchResult], Optional[str]]:
    slug = _slugify_location(location)
    url = f"https://www.realtor.com/apartments/{slug}"

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return [], f"realtor.com returned {response.status_code}"
            soup = BeautifulSoup(response.text, "lxml")
    except Exception as exc:
        return [], str(exc)

    results: list[SearchResult] = []
    for card in soup.select(
        "[data-testid='property-card'], .card-anchor, article"
    )[:MAX_RESULTS_PER_SOURCE]:
        link = card.select_one("a[href*='/apartments/'], a[href*='realtor.com']")
        if not link:
            continue
        listing_url = urljoin(url, link.get("href", ""))
        title = link.get_text(strip=True) or "Realtor.com listing"
        text = card.get_text(" ", strip=True)
        rent = _parse_price(text)
        beds, baths = _parse_beds_baths(text)
        photos = []
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                photos.append(src)
        if title and "realtor" in listing_url:
            results.append(
                SearchResult(
                    title=title[:200],
                    url=listing_url,
                    source_site="realtor.com",
                    rent=rent,
                    bedrooms=beds,
                    bathrooms=baths,
                    snippet=text[:300],
                    photos=photos,
                    location=location,
                )
            )
    return results, None


def search_all_sources(profile: StudentProfile) -> dict:
    location = profile.campus_location or profile.university or ""
    max_rent = profile.max_rent or 2000

    sources = [
        ("apartments.com", search_apartments_com),
        ("rent.com", search_rent_com),
        ("zillow.com", search_zillow),
        ("craigslist", search_craigslist),
        ("realtor.com", search_realtor),
    ]

    all_results: list[SearchResult] = []
    sources_searched: list[str] = []
    errors: dict[str, str] = {}

    for name, searcher in sources:
        results, error = searcher(location, max_rent)
        sources_searched.append(name)
        if error:
            errors[name] = error
        all_results.extend(results)

    seen_urls: set[str] = set()
    unique: list[SearchResult] = []
    for item in all_results:
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        unique.append(item)

    if max_rent:
        unique.sort(
            key=lambda r: (
                0 if r.rent and r.rent <= max_rent else 1,
                -(r.rent or 0),
            )
        )

    return {
        "results": unique[:20],
        "sources_searched": sources_searched,
        "errors": errors,
        "location": location,
        "max_rent": max_rent,
    }


def search_result_to_raw_text(result: SearchResult) -> str:
    lines = [
        result.title,
        result.url,
        f"Source: {result.source_site}",
        f"Location: {result.location}",
    ]
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

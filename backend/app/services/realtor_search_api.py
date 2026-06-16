"""Realtor.com rental search via the public GraphQL API (HTML pages are rate-limited)."""

from typing import Any, Optional

from app.services.image_quality import normalize_photo_list
from app.services.location_parse import ParsedLocation

REALTOR_GQL_URL = "https://www.realtor.com/frontdoor/graphql"

REALTOR_GQL_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Origin": "https://www.realtor.com",
    "Pragma": "no-cache",
    "Referer": "https://www.realtor.com/",
    "rdc-client-name": "RDC_WEB_SRP_FS_PAGE",
    "rdc-client-version": "3.0.2515",
    "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "x-is-bot": "false",
}

SEARCH_SUGGESTIONS_QUERY = """
query Search_suggestions($searchInput: SearchSuggestionsInput!) {
  search_suggestions(search_input: $searchInput) {
    geo_results {
      text
      geo { city state_code area_type }
    }
  }
}
"""

SEARCH_RESULTS_FRAGMENT = """
{
  __typename
  count
  total
  results {
    property_id
    href
    permalink
    list_price
    list_price_min
    list_price_max
    description { beds baths name sqft }
    location {
      address {
        line
        city
        state_code
        postal_code
        coordinate { lat lon }
      }
    }
    primary_photo(https: true) { href }
    photos(https: true, limit: 3) { href }
  }
}
"""


def _minify_query(query: str) -> str:
    return " ".join(query.split())


def _graphql_post(
    operation_name: str,
    query: str,
    variables: dict,
    timeout: float = 25.0,
) -> dict[str, Any]:
    from curl_cffi import requests as curl_requests

    payload = {
        "operationName": operation_name,
        "query": _minify_query(query),
        "variables": variables,
    }
    response = curl_requests.post(
        REALTOR_GQL_URL,
        json=payload,
        headers=REALTOR_GQL_HEADERS,
        timeout=timeout,
        impersonate="chrome131",
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        messages = [
            str(err.get("message", err)) for err in data["errors"] if err
        ]
        raise RuntimeError("; ".join(messages) or "Realtor GraphQL error")
    return data


def _resolve_search_location(parsed: ParsedLocation) -> str:
    if parsed.is_usable_for_search:
        return f"{parsed.city}, {parsed.state.upper()}"
    return parsed.raw.strip()


def _rent_from_item(item: dict) -> Optional[float]:
    for key in ("list_price", "list_price_min", "list_price_max"):
        value = item.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _item_to_dict(item: dict) -> dict:
    location = item.get("location") or {}
    address = location.get("address") if isinstance(location, dict) else {}
    if not isinstance(address, dict):
        address = {}

    line = address.get("line") or ""
    city = address.get("city") or ""
    state = address.get("state_code") or ""
    title = line or item.get("description", {}).get("name") or "Realtor.com listing"
    if city and state and line:
        listing_address = f"{line}, {city}, {state}"
    elif city and state:
        listing_address = f"{city}, {state}"
    else:
        listing_address = str(line or city)

    href = item.get("href") or ""
    if href and not href.startswith("http"):
        href = f"https://www.realtor.com{href}"

    photo_urls: list[str] = []
    primary = item.get("primary_photo")
    if isinstance(primary, dict) and primary.get("href"):
        photo_urls.append(str(primary["href"]))
    for photo in item.get("photos") or []:
        if isinstance(photo, dict) and photo.get("href"):
            photo_urls.append(str(photo["href"]))

    desc = item.get("description") or {}
    beds = desc.get("beds") if isinstance(desc, dict) else None
    baths = desc.get("baths") if isinstance(desc, dict) else None

    coordinate = address.get("coordinate") if isinstance(address, dict) else {}
    lat = coordinate.get("lat") if isinstance(coordinate, dict) else None
    lng = coordinate.get("lon") if isinstance(coordinate, dict) else None

    rent = _rent_from_item(item)
    snippet_parts = []
    if rent:
        snippet_parts.append(f"${int(rent)}/mo")
    if beds is not None:
        snippet_parts.append(f"{beds} bed")
    if baths is not None:
        snippet_parts.append(f"{baths} bath")

    return {
        "title": str(title)[:200],
        "url": href,
        "rent": rent,
        "bedrooms": float(beds) if beds is not None else None,
        "bathrooms": float(baths) if baths is not None else None,
        "snippet": " · ".join(snippet_parts),
        "photos": normalize_photo_list(photo_urls, "realtor.com", limit=5),
        "listing_address": listing_address,
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lng) if lng is not None else None,
    }


def search_realtor_rentals(
    parsed: ParsedLocation,
    max_rent: float,
    *,
    limit: int = 24,
) -> tuple[list[dict], Optional[str]]:
    """Search Realtor.com rentals for a city via GraphQL."""
    location = _resolve_search_location(parsed)
    if not location:
        return [], "Could not parse city/state from campus location"

    try:
        suggest = _graphql_post(
            "Search_suggestions",
            SEARCH_SUGGESTIONS_QUERY,
            {"searchInput": {"search_term": location}},
        )
        geo_results = (
            suggest.get("data", {})
            .get("search_suggestions", {})
            .get("geo_results")
            or []
        )
        if geo_results and geo_results[0].get("text"):
            location = str(geo_results[0]["text"])

        price_filter = ""
        if max_rent:
            price_filter = f"list_price: {{ max: {int(max_rent)} }}"

        query = f"""
        query GetHomeSearch($search_location: SearchLocation, $offset: Int) {{
          homeSearch: home_search(
            query: {{
              status: for_rent
              search_location: $search_location
              {price_filter}
            }}
            bucket: {{ sort: "fractal_v1.1.3_fr" }}
            limit: {min(limit, 50)}
            offset: $offset
          ) {SEARCH_RESULTS_FRAGMENT}
        }}
        """

        response = _graphql_post(
            "GetHomeSearch",
            query,
            {"search_location": {"location": location}, "offset": 0},
        )
        results = (
            response.get("data", {})
            .get("homeSearch", {})
            .get("results")
            or []
        )
        items = [_item_to_dict(item) for item in results if isinstance(item, dict)]
        items = [item for item in items if item.get("url")]
        if not items:
            return [], "No realtor.com rentals found for this area"
        return items[:limit], None
    except ImportError:
        return [], "Realtor search requires curl_cffi (pip install curl_cffi)"
    except Exception as exc:
        return [], f"Realtor.com search failed: {exc}"

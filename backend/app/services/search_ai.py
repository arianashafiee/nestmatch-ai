import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

from openai import OpenAI

from app.config import settings
from app.models import StudentProfile
from app.services.listing_search import SearchResult
from app.services.location_parse import ParsedLocation
from app.services.profile_requirements import (
    bedroom_requirement_label,
    listing_matches_bedroom_requirement,
    occupant_count,
    required_bedrooms,
    unit_rent_budget_limit,
)

MAX_AI_DISCOVERED = 24

SEARCH_ENRICH_SCHEMA = {
    "type": "object",
    "properties": {
        "ranked_indices": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Listing indices ordered best match first",
        },
        "enrichments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "title": {"type": "string"},
                    "snippet": {"type": "string"},
                    "rent": {"type": ["number", "null"]},
                    "bedrooms": {"type": ["number", "null"]},
                    "bathrooms": {"type": ["number", "null"]},
                    "fit_note": {"type": "string"},
                },
                "required": ["index", "title", "snippet", "rent", "bedrooms", "bathrooms", "fit_note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ranked_indices", "enrichments"],
    "additionalProperties": False,
}

AI_DISCOVERY_SCHEMA = {
    "type": "object",
    "properties": {
        "listings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "rent": {"type": ["number", "null"]},
                    "bedrooms": {"type": ["number", "null"]},
                    "bathrooms": {"type": ["number", "null"]},
                    "snippet": {"type": "string"},
                    "listing_address": {"type": "string"},
                },
                "required": [
                    "title",
                    "url",
                    "rent",
                    "bedrooms",
                    "bathrooms",
                    "snippet",
                    "listing_address",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["listings"],
    "additionalProperties": False,
}


def _response_output_text(response: Any) -> str:
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "output_text" and part.text:
                chunks.append(part.text)
    return "".join(chunks).strip()


def _source_site_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "craigslist" in host:
        return "craigslist"
    if "zillow" in host:
        return "zillow.com"
    if "apartments.com" in host:
        return "apartments.com"
    if "rent.com" in host:
        return "rent.com"
    if "realtor.com" in host:
        return "realtor.com"
    if "trulia" in host:
        return "trulia.com"
    return "web"


def _normalize_listing_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    if not cleaned.startswith(("http://", "https://")):
        return ""
    return cleaned


def discover_listings_with_ai_web_search(
    profile: StudentProfile,
    parsed: ParsedLocation,
    *,
    search_area: str,
) -> tuple[list[SearchResult], Optional[str]]:
    """
    Use OpenAI web search to find rentals with the required bedroom count
    near the student's campus address.
    """
    if not settings.openai_api_key:
        return [], None

    campus = profile.campus_location or profile.university or search_area
    beds_required = required_bedrooms(profile)
    beds_label = bedroom_requirement_label(profile)
    max_rent = profile.max_rent or 2000
    max_commute = profile.max_commute_minutes or 30
    commute_mode = profile.commute_mode or "walking"
    occupants = occupant_count(profile)
    unit_budget = unit_rent_budget_limit(profile)

    prompt = f"""Find currently available rental homes or apartments near this campus address:
{campus}

Search area: {search_area}

Student needs:
- Exactly {beds_required} bedrooms ({beds_label})
- Personal budget: ${int(max_rent)}/mo per person ({occupants} people sharing rent unless listing says per person)
- Total unit rent up to about ${int(unit_budget)}/mo when rent is for the whole place
- Within about {max_commute} minutes {commute_mode} commute to campus
- Must-haves: {", ".join(profile.must_haves or []) or "none"}
- Dealbreakers: {", ".join(profile.dealbreakers or []) or "none"}

Search rental listing sites (Zillow, Craigslist, Apartments.com, Rent.com, Realtor.com, Trulia).
Return up to {MAX_AI_DISCOVERED} real listings with direct listing page URLs.
Only include listings that match the required bedroom count when bedroom count is known.
Include street address or neighborhood when available."""

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.responses.create(
            model=settings.openai_model,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ai_discovered_listings",
                    "strict": True,
                    "schema": AI_DISCOVERY_SCHEMA,
                }
            },
        )
        raw = _response_output_text(response)
        if not raw:
            return [], "GPT search returned no listings"
        data = json.loads(raw)
    except Exception as exc:
        return [], str(exc)

    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    for item in data.get("listings", []):
        url = _normalize_listing_url(str(item.get("url", "")))
        if not url or url in seen_urls:
            continue
        if not re.match(r"^https?://", url):
            continue
        seen_urls.add(url)

        title = str(item.get("title") or "Rental listing")[:200]
        snippet = str(item.get("snippet") or "")[:400]
        listing_address = str(item.get("listing_address") or "").strip()
        rent = item.get("rent")
        bedrooms = item.get("bedrooms")
        bathrooms = item.get("bathrooms")

        result = SearchResult(
            title=title,
            url=url,
            source_site=_source_site_from_url(url),
            rent=float(rent) if rent is not None else None,
            bedrooms=float(bedrooms) if bedrooms is not None else None,
            bathrooms=float(bathrooms) if bathrooms is not None else None,
            snippet=snippet or f"Found via GPT search near {search_area}.",
            location=search_area,
            listing_address=listing_address,
        )
        if listing_matches_bedroom_requirement(
            bedrooms=result.bedrooms,
            title=result.title,
            snippet=result.snippet,
            required=beds_required,
        ):
            results.append(result)
        if len(results) >= MAX_AI_DISCOVERED:
            break

    if not results:
        return [], f"GPT search found no {beds_label} listings near campus"
    return results, None


def _compact_results(results: list[SearchResult]) -> list[dict]:
    compact: list[dict] = []
    for index, result in enumerate(results):
        compact.append(
            {
                "index": index,
                "title": result.title,
                "source_site": result.source_site,
                "url": result.url,
                "rent": result.rent,
                "bedrooms": result.bedrooms,
                "bathrooms": result.bathrooms,
                "snippet": result.snippet[:400],
                "listing_address": result.listing_address,
                "commute_minutes": result.commute_minutes,
                "distance_miles": result.distance_miles,
            }
        )
    return compact


def enrich_search_results_with_ai(
    results: list[SearchResult],
    profile: StudentProfile,
) -> tuple[list[SearchResult], Optional[str]]:
    """
    Use OpenAI to rank scraped listings and fill in missing details from snippets.
    Does not browse the web — works on listings already found by our site scrapers.
    """
    if not settings.openai_api_key or len(results) < 2:
        return results, None

    client = OpenAI(api_key=settings.openai_api_key)
    payload = _compact_results(results)
    beds_required = required_bedrooms(profile)
    beds_label = bedroom_requirement_label(profile)
    occupants = occupant_count(profile)
    prompt = f"""You help college students compare apartment search results already scraped from rental sites.

STUDENT PROFILE:
- Campus: {profile.campus_location or profile.university}
- Max rent: ${profile.max_rent}/mo per person ({occupants} people sharing unless listing says per person)
- Max commute: {profile.max_commute_minutes} min by {profile.commute_mode}
- Living situation: {profile.living_situation}
- Roommates: {profile.roommate_count}
- Required bedrooms: {beds_required} ({beds_label})
- Must-haves: {", ".join(profile.must_haves or []) or "none"}
- Dealbreakers: {", ".join(profile.dealbreakers or []) or "none"}

LISTINGS (JSON):
{json.dumps(payload, ensure_ascii=False)}

Tasks:
1. Rank listings by best fit for this student (required bedrooms first, then per-person budget, commute, dealbreakers).
2. EXCLUDE from ranked_indices any listing that clearly does not offer {beds_required} bedrooms.
3. When comparing rent to budget: pick the price tier matching the required {beds_required} bedrooms in ranges like '\$999 - \$2,299 · 1 - 4 Beds' (use \$2,299 for 4-bed, not the studio price). Unless the listing says per person, divide that unit rent by {occupants} to get each person's share.
4. For each listing, write a cleaner title and a 1-2 sentence snippet summarizing why it may fit.
5. Infer rent/bedrooms/bathrooms from snippet text when missing (use null if unknown).
6. fit_note: one short phrase like "4 bed, $1,200/person" or "wrong bedroom count".

Return ranked_indices (only matching listings, best first) and enrichments for every included index."""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You analyze rental listing search results for students. Respond only with JSON matching the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "search_enrichment",
                    "strict": True,
                    "schema": SEARCH_ENRICH_SCHEMA,
                },
            },
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            return results, None
        data = json.loads(content)
    except Exception as exc:
        return results, str(exc)

    enrichments = {item["index"]: item for item in data.get("enrichments", [])}
    ranked_indices = data.get("ranked_indices") or list(range(len(results)))

    reordered: list[SearchResult] = []
    seen: set[int] = set()
    for index in ranked_indices:
        if not isinstance(index, int) or index < 0 or index >= len(results):
            continue
        if index in seen:
            continue
        seen.add(index)
        result = results[index]
        enrichment = enrichments.get(index)
        if enrichment:
            if enrichment.get("title"):
                result.title = str(enrichment["title"])[:200]
            note = enrichment.get("fit_note", "")
            snippet = str(enrichment.get("snippet") or result.snippet)
            if note and note not in snippet:
                snippet = f"{note}. {snippet}" if snippet else note
            result.snippet = snippet[:400]
            if result.rent is None and enrichment.get("rent") is not None:
                result.rent = float(enrichment["rent"])
            if result.bedrooms is None and enrichment.get("bedrooms") is not None:
                result.bedrooms = float(enrichment["bedrooms"])
            if result.bathrooms is None and enrichment.get("bathrooms") is not None:
                result.bathrooms = float(enrichment["bathrooms"])
        reordered.append(result)

    filtered: list[SearchResult] = []
    for result in reordered:
        if listing_matches_bedroom_requirement(
            bedrooms=result.bedrooms,
            title=result.title,
            snippet=result.snippet,
            required=beds_required,
        ):
            filtered.append(result)

    for index, result in enumerate(results):
        if index in seen:
            continue
        if listing_matches_bedroom_requirement(
            bedrooms=result.bedrooms,
            title=result.title,
            snippet=result.snippet,
            required=beds_required,
        ):
            filtered.append(result)

    return filtered, None

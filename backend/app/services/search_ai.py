import json
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.models import StudentProfile
from app.services.listing_search import SearchResult

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
    prompt = f"""You help college students compare apartment search results already scraped from rental sites.

STUDENT PROFILE:
- Campus: {profile.campus_location or profile.university}
- Max rent: ${profile.max_rent}/mo
- Max commute: {profile.max_commute_minutes} min by {profile.commute_mode}
- Must-haves: {", ".join(profile.must_haves or []) or "none"}
- Dealbreakers: {", ".join(profile.dealbreakers or []) or "none"}

LISTINGS (JSON):
{json.dumps(payload, ensure_ascii=False)}

Tasks:
1. Rank listings by best fit for this student (budget, commute, beds, dealbreakers).
2. For each listing, write a cleaner title and a 1-2 sentence snippet summarizing why it may fit.
3. Infer rent/bedrooms/bathrooms from snippet text when missing (use null if unknown).
4. fit_note: one short phrase like "Under budget, 12 min walk" or "Over budget".

Return ranked_indices (all listing indices, best first) and enrichments for every listing index."""

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

    for index, result in enumerate(results):
        if index not in seen:
            reordered.append(result)

    return reordered, None

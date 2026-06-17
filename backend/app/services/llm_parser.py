import json
from typing import Literal, Tuple

from openai import OpenAI

from app.config import settings
from app.models import StudentProfile
from app.schemas import ListingAnalysis
from app.services.listing_address import resolve_map_location
from app.services.mock_parser import parse_listing_mock

LISTING_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "rent_monthly": {"type": ["number", "null"]},
        "location": {"type": "string"},
        "bedrooms": {"type": ["number", "null"]},
        "bathrooms": {"type": ["number", "null"]},
        "amenities": {"type": "array", "items": {"type": "string"}},
        "hidden_fees": {"type": "array", "items": {"type": "string"}},
        "lease_length": {"type": ["string", "null"]},
        "red_flags": {"type": "array", "items": {"type": "string"}},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "estimated_commute_minutes": {"type": ["integer", "null"]},
        "compatibility_score": {"type": "integer"},
        "score_breakdown": {
            "type": "object",
            "properties": {
                "affordability": {"type": "integer"},
                "commute": {"type": "integer"},
                "amenities": {"type": "integer"},
                "safety_comfort": {"type": "integer"},
                "student_fit": {"type": "integer"},
            },
            "required": [
                "affordability",
                "commute",
                "amenities",
                "safety_comfort",
                "student_fit",
            ],
            "additionalProperties": False,
        },
        "pros": {"type": "array", "items": {"type": "string"}},
        "cons": {"type": "array", "items": {"type": "string"}},
        "follow_up_questions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
    },
    "required": [
        "title",
        "rent_monthly",
        "location",
        "bedrooms",
        "bathrooms",
        "amenities",
        "hidden_fees",
        "lease_length",
        "red_flags",
        "missing_info",
        "estimated_commute_minutes",
        "compatibility_score",
        "score_breakdown",
        "pros",
        "cons",
        "follow_up_questions",
    ],
    "additionalProperties": False,
}


def _build_prompt(listing_text: str, profile: StudentProfile) -> str:
    return f"""You are NestMatch AI, an apartment analyst for college students.

Analyze the apartment listing below against the student's profile. Extract all available details, compare against budget and preferences, flag scams/red flags, and score compatibility.

STUDENT PROFILE:
- University: {profile.university}
- Campus location: {profile.campus_location}
- Max monthly rent: ${profile.max_rent}
- Max commute: {profile.max_commute_minutes} minutes by {profile.commute_mode}
- Living situation: {profile.living_situation}
- Roommates: {profile.roommate_count}
- Must-haves: {", ".join(profile.must_haves or []) or "none"}
- Dealbreakers: {", ".join(profile.dealbreakers or []) or "none"}
- Preferred lease length: {profile.preferred_lease_length or "not specified"}

LISTING TEXT:
{listing_text}

INSTRUCTIONS:
1. Extract rent, location, bed/bath, amenities, hidden fees, lease length.
2. For location, use the listing's street address if present (e.g. "123 Main St, Baltimore, MD"). Do NOT use the student's campus address as the listing location.
3. Compare against student budget and dealbreakers.
4. Calculate compatibility_score (0-100) with score_breakdown for: affordability, commute, amenities, safety_comfort, student_fit (each 0-100).
5. Flag standard rental scams/red flags (price too low, wire transfer requests, vague listings, etc.).
6. List missing_info the listing doesn't mention.
7. Provide pros and cons relative to the student profile.
8. Generate exactly 3 specific follow_up_questions for the landlord.
"""


def parse_listing_openai(
    listing_text: str,
    profile: StudentProfile,
) -> ListingAnalysis:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": "You extract and analyze apartment listings for students. Respond only with valid JSON matching the schema.",
            },
            {"role": "user", "content": _build_prompt(listing_text, profile)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "listing_analysis",
                "strict": True,
                "schema": LISTING_ANALYSIS_SCHEMA,
            },
        },
        temperature=0.3,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from OpenAI")
    data = json.loads(content)
    analysis = ListingAnalysis.model_validate(data)
    map_location = resolve_map_location(listing_text, profile, analysis.location)
    if map_location:
        analysis.location = map_location
    return analysis


def parse_listing(
    listing_text: str,
    profile: StudentProfile,
    photo_count: int = 0,
) -> Tuple[ListingAnalysis, Literal["openai", "mock"]]:
    if settings.openai_api_key:
        try:
            return parse_listing_openai(listing_text, profile), "openai"
        except Exception:
            pass
    return parse_listing_mock(listing_text, profile, photo_count=photo_count), "mock"

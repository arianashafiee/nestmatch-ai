import json
import re
from typing import Optional

from app.models import StudentProfile
from app.schemas import ListingAnalysis, ScoreBreakdown
from app.services.profile_requirements import (
    listing_rent_is_per_person,
    occupant_count,
    rent_per_person_for_profile,
    unit_rent_for_profile,
)
from app.services.jhu_housing import (
    compute_homewood_commute_minutes,
    extract_jhu_homewood_distance_from_text,
)

AMENITY_KEYWORDS = {
    "laundry": ["laundry", "washer", "dryer", "w/d"],
    "parking": ["parking", "garage", "driveway"],
    "ac": ["a/c", "ac", "air conditioning", "central air"],
    "furnished": ["furnished", "furniture included"],
    "no_basements": ["basement", "garden level", "lower level"],
}

RENT_PATTERNS = [
    re.compile(r"total monthly price\s*\$?\s*([\d,]+(?:\.\d{2})?)", re.I),
    re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)\s*/?\s*mo", re.I),
    re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s+)?month", re.I),
    re.compile(r"([\d,]+(?:\.\d{2})?)\s*/\s*mo", re.I),
    re.compile(r"rent[:\s]+\$?\s*([\d,]+)", re.I),
]

BED_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:br|bed|bedroom)", re.I),
    re.compile(r"studio", re.I),
]

BATH_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:ba|bath|bathroom)", re.I),
]


def _extract_rent(text: str) -> Optional[float]:
    for pattern in RENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def _extract_beds(text: str) -> Optional[float]:
    if re.search(r"studio", text, re.I):
        return 0
    for pattern in BED_PATTERNS:
        match = pattern.search(text)
        if match and pattern.pattern != "studio":
            return float(match.group(1))
    return None


def _extract_baths(text: str) -> Optional[float]:
    for pattern in BATH_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _text_has_amenity(text: str, tag: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in AMENITY_KEYWORDS.get(tag, []))


def _first_line_title(text: str) -> str:
    for line in text.strip().splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("http"):
            return cleaned[:120]
    return "Apartment Listing"


def _profile_defaults(profile: StudentProfile) -> dict:
    return {
        "max_rent": profile.max_rent or 1500,
        "max_commute": profile.max_commute_minutes or 30,
        "university": profile.university or "",
        "campus": profile.campus_location or profile.university or "campus",
        "commute_mode": profile.commute_mode or "walking",
        "living_situation": profile.living_situation or "solo",
        "roommate_count": profile.roommate_count or 0,
        "occupant_count": occupant_count(profile),
        "must_haves": profile.must_haves or [],
        "dealbreakers": profile.dealbreakers or [],
    }


def parse_listing_mock(
    listing_text: str,
    profile: StudentProfile,
    photo_count: int = 0,
) -> ListingAnalysis:
    text = listing_text.strip()
    prefs = _profile_defaults(profile)
    rent = _extract_rent(text)
    beds = _extract_beds(text)
    baths = _extract_baths(text)
    title = _first_line_title(text)

    campus = prefs["campus"]
    address = extract_listing_address(text)
    if address:
        location = address
    elif campus.lower() in text.lower():
        location = campus
    else:
        location = f"Near {campus}"

    amenities = []
    for tag, keywords in AMENITY_KEYWORDS.items():
        if any(kw in text.lower() for kw in keywords):
            amenities.append(tag.replace("_", " ").title())

    hidden_fees = []
    if "utilities" not in text.lower():
        hidden_fees.append("Utilities responsibility unclear")
    if "deposit" not in text.lower():
        hidden_fees.append("Security deposit not mentioned")

    red_flags = []
    if rent and rent < profile.max_rent * 0.45:
        red_flags.append("Price suspiciously low for the area — possible scam")
    if "wire transfer" in text.lower() or "western union" in text.lower():
        red_flags.append("Requests wire transfer — common rental scam")
    if photo_count == 0 and ("no photos" in text.lower() or len(text) < 80):
        red_flags.append("Very little detail or no photos available")
    elif photo_count > 0:
        pass  # photos fetched from listing page

    missing_info = []
    if rent is None:
        missing_info.append("Monthly rent not clearly stated")
    if beds is None:
        missing_info.append("Bedroom count unclear")

    lease_length = None
    lease_match = re.search(r"(\d+\s*(?:month|year|week)s?\s+lease)", text, re.I)
    if lease_match:
        lease_length = lease_match.group(1)
    elif "lease length:" in text.lower():
        for line in text.splitlines():
            if line.lower().startswith("lease length:"):
                lease_length = line.split(":", 1)[1].strip()
                break
    elif "12" in text and "month" in text.lower():
        lease_length = "12 months"
    if not lease_length:
        missing_info.append("Lease length not specified")
    if "laundry" not in text.lower():
        missing_info.append("Laundry situation not described")

    jhu_distance = extract_jhu_homewood_distance_from_text(text)
    jhu_commute = None
    if jhu_distance is not None:
        jhu_commute = compute_homewood_commute_minutes(
            jhu_distance, prefs["commute_mode"]
        )
    if jhu_commute is not None:
        estimated_commute = jhu_commute
    else:
        estimated_commute = min(
            prefs["max_commute"] + 5,
            max(8, prefs["max_commute"] - 10),
        )

    affordability = 70
    max_rent = prefs["max_rent"]
    rent_for_budget = rent
    if rent:
        rent_for_budget = rent_per_person_for_profile(
            rent,
            profile,
            extra_text=text,
        )
    if rent_for_budget:
        if rent_for_budget <= max_rent:
            affordability = max(55, int(100 - ((rent_for_budget / max_rent) * 35)))
        else:
            over = ((rent_for_budget - max_rent) / max_rent) * 100
            affordability = max(10, int(50 - over))

    commute_score = 75
    max_commute = prefs["max_commute"]
    if estimated_commute <= max_commute:
        commute_score = max(60, int(100 - estimated_commute))
    else:
        commute_score = max(20, int(60 - (estimated_commute - max_commute) * 2))

    amenities_score = 60
    must_haves = prefs["must_haves"]
    if must_haves:
        matched = sum(1 for tag in must_haves if _text_has_amenity(text, tag))
        amenities_score = int((matched / len(must_haves)) * 100)
    elif amenities:
        amenities_score = min(90, 50 + len(amenities) * 8)

    dealbreakers = prefs["dealbreakers"]
    safety_comfort = 80
    for tag in dealbreakers:
        if _text_has_amenity(text, tag):
            safety_comfort -= 25
    safety_comfort = max(10, safety_comfort)
    if red_flags:
        safety_comfort = max(10, safety_comfort - len(red_flags) * 10)

    student_fit = 70
    if prefs["living_situation"] == "roommates" and beds and beds >= 2:
        student_fit += 15
    if rent_for_budget and rent_for_budget <= max_rent * 0.85:
        student_fit += 10
    student_fit = min(100, student_fit)

    breakdown = ScoreBreakdown(
        affordability=affordability,
        commute=commute_score,
        amenities=amenities_score,
        safety_comfort=safety_comfort,
        student_fit=student_fit,
    )
    compatibility_score = int(
        breakdown.affordability * 0.3
        + breakdown.commute * 0.25
        + breakdown.amenities * 0.2
        + breakdown.safety_comfort * 0.15
        + breakdown.student_fit * 0.1
    )

    pros = []
    cons = []
    occupants = prefs["occupant_count"]
    per_person_listing = listing_rent_is_per_person(extra_text=text)
    unit_rent = unit_rent_for_profile(rent, profile, extra_text=text) if rent else None
    if rent_for_budget and rent_for_budget <= max_rent:
        if occupants > 1 and unit_rent and not per_person_listing:
            pros.append(
                f"Your share is about ${int(rent_for_budget)}/mo "
                f"(${int(unit_rent)}/mo total split among {occupants})"
            )
        else:
            pros.append(f"Within your ${int(max_rent)}/mo budget")
    elif rent_for_budget:
        over = int(rent_for_budget - max_rent)
        if occupants > 1 and unit_rent and not per_person_listing:
            cons.append(
                f"Your share is about ${int(rent_for_budget)}/mo "
                f"(${int(unit_rent)}/mo total) — ${over} over your ${int(max_rent)}/mo budget"
            )
        else:
            cons.append(f"Above your ${int(max_rent)}/mo budget by ${over}")
    if jhu_commute is not None:
        mode = prefs["commute_mode"]
        if jhu_commute <= max_commute:
            pros.append(
                f"{jhu_commute} min {mode} to Homewood fits your {max_commute} min limit"
            )
        else:
            cons.append(
                f"{jhu_commute} min {mode} to Homewood exceeds your {max_commute} min limit"
            )
    elif estimated_commute <= max_commute:
        pros.append(
            f"Estimated {estimated_commute} min commute fits your {max_commute} min limit"
        )
    else:
        cons.append(
            f"Estimated {estimated_commute} min commute exceeds your {max_commute} min limit"
        )
    for tag in must_haves:
        if _text_has_amenity(text, tag):
            pros.append(f"Has your must-have: {tag.replace('_', ' ')}")
        else:
            cons.append(f"Missing must-have: {tag.replace('_', ' ')}")
    if not pros:
        pros.append("Worth investigating if other factors align")
    if photo_count > 0:
        pros.insert(0, f"{photo_count} photos loaded from the listing page")
    if not cons:
        cons.append("Limited listing detail — verify before touring")

    questions = [
        "Is laundry in-unit, in-building, or coin-operated?",
        "What utilities are included, and what is the typical monthly total?",
        "What is the lease length and are there move-in fees or deposits?",
    ]
    if "parking" in must_haves:
        questions[0] = "Is parking included or available for an extra fee?"
    if rent is None:
        questions[1] = "What is the exact monthly rent and are there any mandatory fees?"

    return ListingAnalysis(
        title=title,
        rent_monthly=rent,
        location=location,
        bedrooms=beds,
        bathrooms=baths,
        amenities=amenities,
        hidden_fees=hidden_fees,
        lease_length=lease_length,
        red_flags=red_flags,
        missing_info=missing_info,
        estimated_commute_minutes=estimated_commute,
        compatibility_score=compatibility_score,
        score_breakdown=breakdown,
        pros=pros[:4],
        cons=cons[:4],
        follow_up_questions=questions[:3],
    )

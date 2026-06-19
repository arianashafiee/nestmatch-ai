import re
from typing import Any, Iterable, Optional

from app.models import StudentProfile

PER_PERSON_RENT_RE = re.compile(
    r"\b(?:"
    r"per\s+(?:person|tenant|occupant|roommate)|"
    r"/\s*person\b|"
    r"each\s+person"
    r")\b",
    re.I,
)

RENT_BED_TIER_STUDIO_RE = re.compile(
    r"\$\s*([\d,]+)\s*-\s*\$\s*([\d,]+)"
    r"(?:\s*/?\s*(?:bedroom?|bd))?"
    r"\s*(?:·|\||-)?\s*"
    r"studio\s*-\s*(\d+)\s*(?:beds?|br|bd)\b",
    re.I,
)

RENT_BED_TIER_NUMERIC_RE = re.compile(
    r"\$\s*([\d,]+)\s*-\s*\$\s*([\d,]+)"
    r"(?:\s*/?\s*(?:bedroom?|bd))?"
    r"\s*(?:·|\||-)?\s*"
    r"(\d+)\s*-\s*(\d+)\s*(?:beds?|br|bd)\b",
    re.I,
)

BEDROOM_COUNT_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:bedrooms?|beds?)\b", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*[-\s]?(?:br|bd)\b", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:br|bd)\s*/", re.I),
    re.compile(r"\b(\d+)\s*/\s*(\d+(?:\.\d+)?)\s*(?:ba|bath|baths)\b", re.I),
]

BEDROOM_RANGE_PATTERNS = [
    re.compile(
        r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:bedrooms?|beds?|br|bd)\b",
        re.I,
    ),
    re.compile(
        r"(\d+)\s*(?:bedrooms?|beds?|br|bd)\s*(?:-|–|to)\s*(\d+)\b",
        re.I,
    ),
    re.compile(r"studio\s*(?:-|–|to)\s*(\d+)\s*(?:beds?|br|bd)\b", re.I),
]


def required_bedrooms(profile: StudentProfile) -> int:
    """Bedrooms needed: solo/studio = 1, roommates = you + roommate count."""
    if profile.living_situation == "roommates" and (profile.roommate_count or 0) > 0:
        return int(profile.roommate_count) + 1
    return 1


def bedroom_requirement_label(profile: StudentProfile) -> str:
    required = required_bedrooms(profile)
    if required == 1:
        return "studio or 1-bedroom"
    return f"{required}-bedroom"


def occupant_count(profile: StudentProfile) -> int:
    """People sharing rent: you + roommates when living with roommates."""
    if profile.living_situation == "roommates" and (profile.roommate_count or 0) > 0:
        return int(profile.roommate_count) + 1
    return 1


def unit_rent_budget_limit(profile: StudentProfile) -> float:
    """Max total unit rent when profile max_rent is the student's personal budget."""
    return (profile.max_rent or 2000) * occupant_count(profile)


def listing_rent_is_per_person(
    *,
    title: str = "",
    snippet: str = "",
    extra_text: str = "",
) -> bool:
    text = f"{title} {snippet} {extra_text}".strip()
    return bool(PER_PERSON_RENT_RE.search(text))


def _parse_money(value: str) -> float:
    return float(value.replace(",", ""))


def _rent_for_bed_in_tier(
    required_beds: int,
    bed_min: int,
    bed_max: int,
    rent_min: float,
    rent_max: float,
) -> float:
    if bed_max <= bed_min:
        return rent_max if required_beds >= bed_max else rent_min
    ratio = (required_beds - bed_min) / (bed_max - bed_min)
    ratio = max(0.0, min(1.0, ratio))
    return rent_min + (rent_max - rent_min) * ratio


def rent_for_bedroom_count(
    text: str,
    required_beds: int,
    *,
    fallback_rent: Optional[float] = None,
) -> Optional[float]:
    """
    Pick the rent tier that matches required bedrooms in range listings like
    '$999 - $2,299 /Bedroom · 1 - 4 Beds' or '$1,440 - $6,344 · Studio - 4 Beds'.
    """
    if not text.strip():
        return fallback_rent

    best: Optional[float] = None
    for pattern, studio_tier in (
        (RENT_BED_TIER_STUDIO_RE, True),
        (RENT_BED_TIER_NUMERIC_RE, False),
    ):
        for match in pattern.finditer(text):
            rent_min = _parse_money(match.group(1))
            rent_max = _parse_money(match.group(2))
            if studio_tier:
                bed_min = 0
                bed_max = int(match.group(3))
            else:
                bed_min = int(match.group(3))
                bed_max = int(match.group(4))

            if required_beds == 1 and bed_min <= 1 <= bed_max:
                tier_rent = _rent_for_bed_in_tier(
                    1, bed_min, bed_max, rent_min, rent_max
                )
                best = tier_rent if best is None else min(best, tier_rent)
                continue

            if bed_min <= required_beds <= bed_max:
                tier_rent = _rent_for_bed_in_tier(
                    required_beds, bed_min, bed_max, rent_min, rent_max
                )
                best = tier_rent if best is None else min(best, tier_rent)

    return best if best is not None else fallback_rent


def unit_rent_for_profile(
    rent: Optional[float],
    profile: StudentProfile,
    *,
    title: str = "",
    snippet: str = "",
    extra_text: str = "",
) -> Optional[float]:
    """Total unit rent for the student's required bedroom count."""
    text = f"{title} {snippet} {extra_text}".strip()
    required = required_bedrooms(profile)
    return rent_for_bedroom_count(text, required, fallback_rent=rent)


def rent_per_person_for_profile(
    rent: float,
    profile: StudentProfile,
    *,
    title: str = "",
    snippet: str = "",
    extra_text: str = "",
) -> float:
    """Personal monthly cost unless the listing already states rent per person."""
    unit_rent = unit_rent_for_profile(
        rent,
        profile,
        title=title,
        snippet=snippet,
        extra_text=extra_text,
    )
    if unit_rent is None:
        unit_rent = rent
    if listing_rent_is_per_person(title=title, snippet=snippet, extra_text=extra_text):
        return unit_rent
    occupants = occupant_count(profile)
    if occupants <= 1:
        return unit_rent
    return unit_rent / occupants


def listing_within_rent_budget(
    rent: Optional[float],
    profile: StudentProfile,
    *,
    title: str = "",
    snippet: str = "",
    extra_text: str = "",
) -> bool:
    if rent is None:
        return True
    unit_rent = unit_rent_for_profile(
        rent,
        profile,
        title=title,
        snippet=snippet,
        extra_text=extra_text,
    )
    if unit_rent is None:
        return True
    per_person = rent_per_person_for_profile(
        unit_rent,
        profile,
        title=title,
        snippet=snippet,
        extra_text=extra_text,
    )
    return per_person <= (profile.max_rent or 2000)


def _add_count(counts: set[int], value: float) -> None:
    if value < 0:
        return
    counts.add(int(round(value)))


def parse_bedroom_counts_from_text(text: str) -> set[int]:
    """Collect every bedroom count mentioned in listing title/snippet text."""
    if not text:
        return set()

    counts: set[int] = set()
    if re.search(r"\bstudio\b", text, re.I):
        counts.add(0)

    for pattern in BEDROOM_RANGE_PATTERNS:
        for match in pattern.finditer(text):
            if "studio" in pattern.pattern.lower() and match.lastindex == 1:
                end = int(match.group(1))
                for bed_count in range(0, end + 1):
                    counts.add(bed_count)
                continue
            start = int(match.group(1))
            end = int(match.group(2))
            low, high = min(start, end), max(start, end)
            for bed_count in range(low, high + 1):
                counts.add(bed_count)

    for pattern in BEDROOM_COUNT_PATTERNS:
        for match in pattern.finditer(text):
            _add_count(counts, float(match.group(1)))

    return counts


def bedroom_counts_from_structured(value: Any) -> set[int]:
    """Normalize bedrooms from scrapers (int, dict min/max, formatted strings)."""
    if value is None:
        return set()

    if isinstance(value, bool):
        return set()

    if isinstance(value, (int, float)):
        return {int(round(float(value)))}

    if isinstance(value, str):
        return parse_bedroom_counts_from_text(value)

    if isinstance(value, dict):
        counts: set[int] = set()
        min_val = value.get("min")
        max_val = value.get("max", min_val)
        low = value.get("low", min_val)
        high = value.get("high", max_val if max_val is not None else low)

        if low is not None:
            lo = int(low)
            hi = int(high if high is not None else low)
            counts.update(range(min(lo, hi), max(lo, hi) + 1))

        for key in ("formattedValue", "formatted", "value", "label"):
            text = value.get(key)
            if isinstance(text, str):
                counts.update(parse_bedroom_counts_from_text(text))

        return counts

    return set()


def normalize_bedroom_scalar(value: Any) -> Optional[float]:
    counts = bedroom_counts_from_structured(value)
    if not counts:
        return None
    return float(max(counts))


def parse_bedrooms_from_text(text: str) -> Optional[float]:
    counts = parse_bedroom_counts_from_text(text)
    if not counts:
        return None
    return float(max(counts))


def expand_bedroom_range(low: float, high: Optional[float] = None) -> set[int]:
    end = int(round(high if high is not None else low))
    start = int(round(low))
    low_bound, high_bound = min(start, end), max(start, end)
    return set(range(low_bound, high_bound + 1))


def listing_offered_bed_counts(
    *,
    bedrooms: Any = None,
    title: str = "",
    snippet: str = "",
    extra_counts: Optional[Iterable[float]] = None,
) -> set[int]:
    counts = parse_bedroom_counts_from_text(f"{title} {snippet}".strip())
    counts.update(bedroom_counts_from_structured(bedrooms))
    if extra_counts:
        for value in extra_counts:
            counts.update(bedroom_counts_from_structured(value))
    return counts


def listing_matches_bedroom_requirement(
    *,
    bedrooms: Any = None,
    title: str = "",
    snippet: str = "",
    required: int,
    extra_counts: Optional[Iterable[float]] = None,
) -> bool:
    counts = listing_offered_bed_counts(
        bedrooms=bedrooms,
        title=title,
        snippet=snippet,
        extra_counts=extra_counts,
    )
    if not counts:
        return False
    if required == 1:
        return 0 in counts or 1 in counts
    return required in counts


def listing_bedrooms(
    *,
    bedrooms: Any = None,
    title: str = "",
    snippet: str = "",
    extra_counts: Optional[Iterable[float]] = None,
) -> Optional[float]:
    counts = listing_offered_bed_counts(
        bedrooms=bedrooms,
        title=title,
        snippet=snippet,
        extra_counts=extra_counts,
    )
    if not counts:
        return None
    scalar = normalize_bedroom_scalar(bedrooms)
    if scalar is not None:
        return scalar
    return parse_bedrooms_from_text(f"{title} {snippet}")


def bedrooms_match_requirement(
    bedrooms: Optional[float],
    required: int,
) -> bool:
    if bedrooms is None:
        return False
    beds = int(round(bedrooms))
    if required == 1:
        return beds in (0, 1)
    return beds == required

import re
from typing import Optional

from app.models import StudentProfile

ADDRESS_LINE = re.compile(r"^Address:\s*(.+)$", re.I | re.M)
STREET_ADDRESS = re.compile(
    r"\b(\d{1,6}\s+"
    r"[A-Za-z0-9.'\-]+(?:\s+[A-Za-z0-9.'\-]+){0,6}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|"
    r"Way|Ct|Court|Pl|Place|Pkwy|Parkway|Cir|Circle|Ter|Terrace|Trl|Trail)"
    r"\.?"
    r"(?:\s*(?:#|Apt|Unit|Suite)\.?\s*[\w\-]+)?"
    r"(?:,\s*[A-Za-z .'\-]+,\s*[A-Z]{2}(?:\s+\d{5}(?:-\d{4})?)?)?)\b",
    re.I,
)


def extract_listing_address(text: str) -> str:
    """Pull a street address from hydrated listing text or search raw_text."""
    if not text:
        return ""

    line_match = ADDRESS_LINE.search(text)
    if line_match:
        address = line_match.group(1).strip()
        if address and not _looks_like_campus_label(address):
            return address

    for match in STREET_ADDRESS.finditer(text):
        candidate = match.group(1).strip()
        if candidate and not _looks_like_campus_label(candidate):
            return candidate

    return ""


def _looks_like_campus_label(value: str) -> bool:
    lower = value.lower()
    campus_words = (
        "campus",
        "university",
        "college",
        "homewood",
        "johns hopkins",
        "near campus",
    )
    if any(word in lower for word in campus_words):
        return True
    if lower.startswith("near "):
        return True
    return False


def resolve_map_location(
    listing_text: str,
    profile: Optional[StudentProfile],
    analysis_location: str = "",
) -> str:
    """Best geocodable location for maps — prefer listing street address."""
    address = extract_listing_address(listing_text)
    if address:
        return address

    if analysis_location and not _looks_like_campus_label(analysis_location):
        return analysis_location

    if profile:
        campus = (profile.campus_location or profile.university or "").strip()
        if campus and _looks_like_campus_label(analysis_location):
            return ""

    return analysis_location.strip()

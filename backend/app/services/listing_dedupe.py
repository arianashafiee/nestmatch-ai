"""Cross-site deduplication for rental search results."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.listing_search import SearchResult

SOURCE_PRIORITY = {
    "jhu_housing": 0,
    "apartments.com": 1,
    "rent.com": 2,
    "zillow.com": 3,
    "craigslist": 4,
    "realtor.com": 5,
}

_STREET_SUFFIXES = {
    "street",
    "st",
    "avenue",
    "ave",
    "road",
    "rd",
    "boulevard",
    "blvd",
    "drive",
    "dr",
    "lane",
    "ln",
    "way",
    "court",
    "ct",
    "place",
    "pl",
    "parkway",
    "pkwy",
    "circle",
    "cir",
    "terrace",
    "ter",
    "trail",
    "trl",
}

_DIRECTIONS = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "n": "n",
    "s": "s",
    "e": "e",
    "w": "w",
}


def _normalize_listing_address(address: str) -> str:
    if not address:
        return ""

    text = address.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\b(?:apt|unit|suite|ste|#)\s*[\w-]+\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d+[a-z]\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = text.split()
    if not tokens or not tokens[0].isdigit():
        return text

    core = [tokens[0]]
    index = 1
    if index < len(tokens) and tokens[index] in _DIRECTIONS.values():
        core.append(tokens[index])
        index += 1
    if index < len(tokens):
        core.append(tokens[index])

    zip_token = next((token for token in tokens if token.isdigit() and len(token) == 5), "")
    state_token = next(
        (token for token in tokens if len(token) == 2 and token.isalpha()),
        "",
    )
    if state_token:
        core.append(f"state{state_token}")
    if zip_token:
        core.append(f"zip{zip_token}")

    return " ".join(core).strip()


def _extract_street_core(text: str) -> str:
    if not text:
        return ""

    cleaned = text.lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    match = re.search(
        r"\b(\d{1,6})\s+"
        r"((?:north|south|east|west|n|s|e|w)\s+)?"
        r"([a-z0-9]+(?:\s+[a-z0-9]+){0,3})",
        cleaned,
    )
    if not match:
        return ""

    number = match.group(1)
    direction = (match.group(2) or "").strip()
    direction_token = _DIRECTIONS.get(direction, direction[:1] if direction else "")
    raw_words = match.group(3).split()
    street_words: list[str] = []
    for word in raw_words:
        if word in _STREET_SUFFIXES or word in _DIRECTIONS:
            break
        if re.fullmatch(r"\d+[a-z]", word, flags=re.I):
            break
        street_words.append(word)
        if len(street_words) >= 2:
            break
    if not street_words:
        return ""

    street = street_words[0] if len(street_words) == 1 else " ".join(street_words[:2])
    if direction_token:
        return f"{number}|{direction_token}|{street}"
    return f"{number}|{street}"


def listing_fingerprints(result: SearchResult) -> list[str]:
    """Build comparable keys for the same unit across rental sites."""
    fingerprints: list[str] = []
    rent = int(round(result.rent)) if result.rent else -1
    beds = int(result.bedrooms) if result.bedrooms is not None else -1

    normalized_address = _normalize_listing_address(result.listing_address)
    if normalized_address and re.search(r"\d", normalized_address):
        fingerprints.append(f"addr:{normalized_address}|r{rent}|b{beds}")

    street = _extract_street_core(result.listing_address) or _extract_street_core(
        result.title
    )
    if street:
        fingerprints.append(f"street:{street}|r{rent}|b{beds}")

    return fingerprints


def prefer_search_result(candidate: SearchResult, incumbent: SearchResult) -> bool:
    """Return True when candidate should replace an existing duplicate."""
    candidate_rank = SOURCE_PRIORITY.get(candidate.source_site, 99)
    incumbent_rank = SOURCE_PRIORITY.get(incumbent.source_site, 99)
    if candidate_rank != incumbent_rank:
        return candidate_rank < incumbent_rank

    if len(candidate.photos) != len(incumbent.photos):
        return len(candidate.photos) > len(incumbent.photos)

    if len(candidate.listing_address) != len(incumbent.listing_address):
        return len(candidate.listing_address) > len(incumbent.listing_address)

    return False


def dedupe_cross_site_results(results: list[SearchResult]) -> list[SearchResult]:
    """Drop duplicate listings that appear on multiple rental sites."""
    kept: list[SearchResult] = []
    fingerprint_index: dict[str, int] = {}

    for result in results:
        duplicate_index: int | None = None
        for fingerprint in listing_fingerprints(result):
            if fingerprint in fingerprint_index:
                duplicate_index = fingerprint_index[fingerprint]
                break

        if duplicate_index is None:
            index = len(kept)
            kept.append(result)
            for fingerprint in listing_fingerprints(result):
                fingerprint_index[fingerprint] = index
            continue

        existing = kept[duplicate_index]
        if prefer_search_result(result, existing):
            kept[duplicate_index] = result
            for fingerprint in listing_fingerprints(result):
                fingerprint_index[fingerprint] = duplicate_index

    return kept

import re
from dataclasses import dataclass
from typing import Optional

STATE_NAME_TO_ABBREV: dict[str, str] = {
    "alabama": "al",
    "alaska": "ak",
    "arizona": "az",
    "arkansas": "ar",
    "california": "ca",
    "colorado": "co",
    "connecticut": "ct",
    "delaware": "de",
    "florida": "fl",
    "georgia": "ga",
    "hawaii": "hi",
    "idaho": "id",
    "illinois": "il",
    "indiana": "in",
    "iowa": "ia",
    "kansas": "ks",
    "kentucky": "ky",
    "louisiana": "la",
    "maine": "me",
    "maryland": "md",
    "massachusetts": "ma",
    "michigan": "mi",
    "minnesota": "mn",
    "mississippi": "ms",
    "missouri": "mo",
    "montana": "mt",
    "nebraska": "ne",
    "nevada": "nv",
    "new hampshire": "nh",
    "new jersey": "nj",
    "new mexico": "nm",
    "new york": "ny",
    "north carolina": "nc",
    "north dakota": "nd",
    "ohio": "oh",
    "oklahoma": "ok",
    "oregon": "or",
    "pennsylvania": "pa",
    "rhode island": "ri",
    "south carolina": "sc",
    "south dakota": "sd",
    "tennessee": "tn",
    "texas": "tx",
    "utah": "ut",
    "vermont": "vt",
    "virginia": "va",
    "washington": "wa",
    "west virginia": "wv",
    "wisconsin": "wi",
    "wyoming": "wy",
    "district of columbia": "dc",
}

VALID_STATE_ABBREVS = set(STATE_NAME_TO_ABBREV.values())


def _normalize_state(raw: str) -> str:
    token = raw.strip().lower()
    if len(token) == 2 and token.isalpha():
        return token
    return STATE_NAME_TO_ABBREV.get(token, "")


def _looks_like_street(text: str) -> bool:
    return bool(re.match(r"^\d+\s", text.strip()))


@dataclass
class ParsedLocation:
    raw: str
    street: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""

    @property
    def city_state(self) -> str:
        if self.city and self.state:
            return f"{self.city}, {self.state.upper()}"
        return self.raw.strip()

    @property
    def search_slug(self) -> str:
        if not self.city or not self.state:
            return ""
        city_slug = re.sub(r"\s+", "-", self.city.strip().lower())
        return f"{city_slug}-{self.state.lower()}"

    @property
    def geocode_query(self) -> str:
        return self.raw.strip()

    @property
    def is_usable_for_search(self) -> bool:
        return bool(self.city and self.state in VALID_STATE_ABBREVS)


def parse_campus_location(text: str) -> ParsedLocation:
    """Extract city/state (and street) from a campus address or city label."""
    raw = (text or "").strip()
    if not raw:
        return ParsedLocation(raw=raw)

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    street = ""
    city = ""
    state = ""
    zip_code = ""

    if len(parts) >= 3:
        state_part = parts[-1]
        city = parts[-2]
        prefix = ", ".join(parts[:-2])
        street = prefix if _looks_like_street(prefix) else ""
        state = _normalize_state(state_part.split()[0])
        zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", state_part)
        if zip_match:
            zip_code = zip_match.group(1)
    elif len(parts) == 2:
        left, right = parts
        right_state = re.match(r"^([A-Za-z]{2})\b(?:\s+(\d{5}))?", right.strip())
        if right_state:
            city = left
            state = _normalize_state(right_state.group(1))
            zip_code = right_state.group(2) or ""
        elif _looks_like_street(left):
            street = left
            city_state = re.match(
                r"^(.+?)\s+([A-Za-z]{2})(?:\s+(\d{5}))?\s*$", right.strip()
            )
            if city_state:
                city = city_state.group(1).strip()
                state = _normalize_state(city_state.group(2))
                zip_code = city_state.group(3) or ""
            else:
                city = right
                state = _normalize_state(right.split()[0])
        else:
            city = left
            state = _normalize_state(right.split()[0])
            zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", right)
            if zip_match:
                zip_code = zip_match.group(1)
    else:
        inline = re.match(
            r"^(.+?)\s+([A-Za-z]{2})(?:\s+(\d{5}))?\s*$", parts[0].strip()
        )
        if inline:
            city = inline.group(1).strip()
            state = _normalize_state(inline.group(2))
            zip_code = inline.group(3) or ""
        else:
            city = parts[0]

    if len(state) > 2:
        state = _normalize_state(state)

    if state and state not in VALID_STATE_ABBREVS:
        state = ""

    return ParsedLocation(
        raw=raw,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
    )

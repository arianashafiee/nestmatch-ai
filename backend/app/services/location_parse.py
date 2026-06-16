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


STREET_SUFFIX = (
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|"
    r"Court|Ct|Place|Pl|Parkway|Pkwy|Circle|Cir|Terrace|Ter)\.?"
)


def _split_street_and_city(combined: str) -> tuple[str, str]:
    """Split '3400 North Charles Street Baltimore' into street + city."""
    text = combined.strip()
    match = re.match(rf"^(\d+\s+.*?{STREET_SUFFIX})\s+(.+)$", text, re.I)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text, ""


def _parse_state_zip(part: str) -> tuple[str, str]:
    """Parse 'MD 21218' or 'Maryland' into (state abbrev, zip)."""
    token = part.strip()
    state_zip = re.match(r"^([A-Za-z]{2})\b(?:\s+(\d{5})(?:-\d{4})?)?\s*$", token)
    if state_zip:
        state = _normalize_state(state_zip.group(1))
        zip_code = state_zip.group(2) or ""
        if state in VALID_STATE_ABBREVS:
            return state, zip_code
    state = _normalize_state(token.split()[0])
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", token)
    zip_code = zip_match.group(1) if zip_match else ""
    return state, zip_code


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
        state, zip_code = _parse_state_zip(right)

        if state in VALID_STATE_ABBREVS and _looks_like_street(left):
            street, city = _split_street_and_city(left)
            if not city:
                city = left
                street = ""
        elif state in VALID_STATE_ABBREVS:
            city = left
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

    # Normalize common "Street City, ST ZIP" without comma before city
    if (
        not city
        and street
        and _looks_like_street(raw)
        and "," not in raw
    ):
        inline_state = re.search(
            r"\b([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?\s*$",
            raw,
        )
        if inline_state:
            state = _normalize_state(inline_state.group(1))
            zip_code = inline_state.group(2)
            prefix = raw[: inline_state.start()].strip()
            street, city = _split_street_and_city(prefix)

    return ParsedLocation(
        raw=raw,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
    )


def normalize_campus_location(text: str) -> str:
    """Format campus addresses for reliable city/state extraction."""
    raw = (text or "").strip()
    if not raw:
        return raw

    parsed = parse_campus_location(raw)
    if not parsed.is_usable_for_search:
        return raw

    if parsed.street:
        suffix = f", {parsed.state.upper()}"
        if parsed.zip_code:
            suffix = f", {parsed.state.upper()} {parsed.zip_code}"
        return f"{parsed.street}, {parsed.city}{suffix}"

    if parsed.zip_code:
        return f"{parsed.city}, {parsed.state.upper()} {parsed.zip_code}"
    return f"{parsed.city}, {parsed.state.upper()}"

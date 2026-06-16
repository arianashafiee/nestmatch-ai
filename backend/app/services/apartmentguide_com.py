"""ApartmentGuide.com search (RentGroup platform — same inventory as Rent.com)."""

from app.services.location_parse import STATE_NAME_TO_ABBREV, ParsedLocation
from app.services.rentgroup_search import (
    build_apartmentguide_listing_url,
    parse_rentgroup_search,
)


def _state_slug(state_abbrev: str) -> str:
    for name, abbr in STATE_NAME_TO_ABBREV.items():
        if abbr == state_abbrev.lower():
            return name.title().replace(" ", "-")
    return state_abbrev.upper()


def apartmentguide_search_url(parsed: ParsedLocation, max_rent: float) -> str:
    if not parsed.is_usable_for_search:
        return ""
    state_slug = _state_slug(parsed.state)
    city_slug = parsed.city.replace(" ", "-")
    url = f"https://www.apartmentguide.com/apartments/{state_slug}/{city_slug}/"
    if max_rent:
        url = f"{url}under-{int(max_rent)}/"
    return url


def parse_apartmentguide_search(html: str, base_url: str) -> list[dict]:
    return parse_rentgroup_search(
        html,
        site="apartmentguide.com",
        listing_url_builder=build_apartmentguide_listing_url,
        limit=50,
    )

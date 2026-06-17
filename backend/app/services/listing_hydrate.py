from app.services.image_quality import normalize_photo_list
from app.services.listing_fetcher import (
    detect_source_site,
    enrich_listing_text,
    fetch_listing_from_url,
    fetched_to_landlord_contact,
)


def apply_fetched_to_listing(listing, fetched) -> None:
    existing = list(listing.photos or [])
    if fetched.photos:
        fetched_photos = normalize_photo_list(
            fetched.photos, fetched.source_site or "", limit=20
        )
        if len(fetched_photos) >= len(existing):
            listing.photos = fetched_photos
    elif existing:
        listing.photos = existing
    if fetched.source_site:
        listing.source_site = fetched.source_site
    contact = fetched_to_landlord_contact(fetched)
    if any(contact.values()):
        listing.landlord_contact = contact


import re


_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:apartments\.com|rent\.com|zillow\.com|"
    r"craigslist\.org|realtor\.com|offcampushousing\.jhu\.edu)[^\s<>\"']+",
    re.I,
)


def extract_url_from_text(text: str):
    match = _URL_RE.search(text)
    if match:
        return match.group(0).strip(".,)")
    for token in text.split():
        if token.startswith("http://") or token.startswith("https://"):
            return token.strip(".,)")
    return None


def hydrate_listing_from_url(
    listing,
    raw_text: str,
    source_url=None,
    fetch_photos: bool = True,
) -> str:
    url = source_url or listing.source_url or extract_url_from_text(raw_text)
    if not url:
        return raw_text

    if detect_source_site(url) == "apartments.com":
        from app.services.apartments_com import canonicalize_apartments_com_listing_url

        url = canonicalize_apartments_com_listing_url(url)

    listing.source_url = url
    listing.source_site = detect_source_site(url)

    if not fetch_photos:
        return raw_text

    fetched = fetch_listing_from_url(url)
    apply_fetched_to_listing(listing, fetched)
    return enrich_listing_text(raw_text, fetched)

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list

REALTOR_LISTING_RE = re.compile(
    r"https://www\.realtor\.com/apartments/[^\s\"'<>]+",
    re.I,
)


def _parse_price(text: str) -> Optional[float]:
    match = re.search(r"\$[\d,]+", text)
    if match:
        return float(match.group().replace("$", "").replace(",", ""))
    return None


def _realtor_location_slug(location: str) -> str:
    cleaned = location.strip()
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            city = parts[0].replace(" ", "-")
            state = parts[1].split()[0].upper()
            return f"{city}_{state}"
    slug = cleaned.lower().replace(" ", "-")
    if "-" in slug:
        city, state = slug.rsplit("-", 1)
        return f"{city.title().replace('-', '-')}_{state.upper()}"
    return cleaned.replace(" ", "_")


def parse_realtor_search(html: str, base_url: str) -> list[dict]:
    """Parse Realtor.com apartment search results."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen_urls: set[str] = set()

    for script in soup.find_all("script", id="__NEXT_DATA__"):
        try:
            data = json.loads(script.string or "{}")
            properties = (
                data.get("props", {})
                .get("pageProps", {})
                .get("properties", [])
            )
            if not properties:
                properties = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("searchResults", {})
                    .get("home_search", {})
                    .get("results", [])
                )
            for item in properties:
                if not isinstance(item, dict):
                    continue
                permalink = item.get("permalink") or item.get("property_id")
                listing_url = item.get("href") or item.get("rdc_web_url")
                if not listing_url and permalink:
                    listing_url = urljoin(base_url, str(permalink))
                if not listing_url:
                    continue
                listing_url = urljoin(base_url, str(listing_url))
                if listing_url in seen_urls:
                    continue
                seen_urls.add(listing_url)
                location = item.get("location") or {}
                address = location.get("address") if isinstance(location, dict) else {}
                line = address.get("line") if isinstance(address, dict) else None
                photos = normalize_photo_list(
                    [
                        str(item["primary_photo"]["href"])
                        for key in ("primary_photo",)
                        if isinstance(item.get("primary_photo"), dict)
                        and item["primary_photo"].get("href")
                    ],
                    "realtor.com",
                    limit=3,
                )
                desc = item.get("description") or {}
                beds = desc.get("beds") if isinstance(desc, dict) else None
                baths = desc.get("baths") if isinstance(desc, dict) else None
                price = None
                if isinstance(desc, dict):
                    price = desc.get("price") or desc.get("list_price")
                results.append(
                    {
                        "title": str(line or item.get("name") or "Realtor.com listing"),
                        "url": listing_url,
                        "rent": float(price) if price else _parse_price(str(item)),
                        "bedrooms": float(beds) if beds is not None else None,
                        "bathrooms": float(baths) if baths is not None else None,
                        "snippet": str(item.get("tags", ""))[:300],
                        "photos": photos,
                    }
                )
        except (json.JSONDecodeError, TypeError, AttributeError, ValueError):
            continue

    for card in soup.select(
        "[data-testid='property-card'], .card-anchor, article[data-test='property-card']"
    ):
        link = card.select_one("a[href*='/apartments/'], a[href*='realtor.com']")
        if not link:
            continue
        listing_url = urljoin(base_url, link.get("href", ""))
        if listing_url in seen_urls or "realtor.com" not in listing_url:
            continue
        seen_urls.add(listing_url)
        text = card.get_text(" ", strip=True)
        photos = []
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                photos = normalize_photo_list([src], "realtor.com", limit=3)
        results.append(
            {
                "title": link.get_text(strip=True) or "Realtor.com listing",
                "url": listing_url,
                "rent": _parse_price(text),
                "snippet": text[:300],
                "photos": photos,
                "bedrooms": None,
                "bathrooms": None,
            }
        )

    for match in REALTOR_LISTING_RE.findall(html):
        listing_url = match.split("?")[0].rstrip("/") + "/"
        if listing_url in seen_urls:
            continue
        if "/apartments/" not in listing_url.lower():
            continue
        seen_urls.add(listing_url)
        slug = listing_url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        results.append(
            {
                "title": slug.title()[:200],
                "url": listing_url,
                "rent": None,
                "snippet": "",
                "photos": [],
                "bedrooms": None,
                "bathrooms": None,
            }
        )

    return results[:12]

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list

ZILLOW_HOMEDETAILS_RE = re.compile(
    r"https://www\.zillow\.com/homedetails/[^\s\"'<>]+",
    re.I,
)


def _parse_price(text: str) -> Optional[float]:
    match = re.search(r"\$[\d,]+", text)
    if match:
        return float(match.group().replace("$", "").replace(",", ""))
    return None


def parse_zillow_search(html: str, base_url: str) -> list[dict]:
    """Parse Zillow rental search results from embedded JSON and DOM."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen_urls: set[str] = set()

    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        try:
            data = json.loads(next_script.string)
            list_results = (
                data.get("props", {})
                .get("pageProps", {})
                .get("searchPageState", {})
                .get("cat1", {})
                .get("searchResults", {})
                .get("listResults", [])
            )
            for item in list_results:
                if not isinstance(item, dict):
                    continue
                detail = item.get("detailUrl") or item.get("hdpUrl")
                if not detail:
                    continue
                listing_url = urljoin(base_url, str(detail))
                if listing_url in seen_urls:
                    continue
                seen_urls.add(listing_url)

                rent = item.get("price") or item.get("unformattedPrice")
                beds = item.get("beds")
                baths = item.get("baths")
                units = item.get("units") or []
                if isinstance(units, list) and units:
                    unit_prices = [
                        u.get("price")
                        for u in units
                        if isinstance(u, dict) and u.get("price")
                    ]
                    if unit_prices and rent is None:
                        rent = min(unit_prices)
                    if beds is None:
                        beds = next(
                            (u.get("beds") for u in units if isinstance(u, dict) and u.get("beds") is not None),
                            None,
                        )
                    if baths is None:
                        baths = next(
                            (
                                u.get("baths")
                                for u in units
                                if isinstance(u, dict) and u.get("baths") is not None
                            ),
                            None,
                        )

                lat_long = item.get("latLong") or {}
                latitude = lat_long.get("latitude") if isinstance(lat_long, dict) else None
                longitude = lat_long.get("longitude") if isinstance(lat_long, dict) else None

                photos = normalize_photo_list(
                    [str(item["imgSrc"])] if item.get("imgSrc") else [],
                    "zillow.com",
                    limit=3,
                )
                title = str(
                    item.get("address")
                    or item.get("statusText")
                    or item.get("buildingName")
                    or "Zillow rental"
                )
                snippet_parts = []
                if rent:
                    snippet_parts.append(f"${int(rent)}/mo")
                if beds is not None:
                    snippet_parts.append(f"{beds} bed")
                if baths is not None:
                    snippet_parts.append(f"{baths} bath")

                results.append(
                    {
                        "title": title[:200],
                        "url": listing_url,
                        "rent": float(rent) if rent is not None else None,
                        "bedrooms": float(beds) if beds is not None else None,
                        "bathrooms": float(baths) if baths is not None else None,
                        "snippet": " · ".join(snippet_parts),
                        "photos": photos,
                        "listing_address": title,
                        "latitude": float(latitude) if latitude is not None else None,
                        "longitude": float(longitude) if longitude is not None else None,
                    }
                )
        except (json.JSONDecodeError, TypeError, AttributeError, ValueError):
            pass

    if len(results) >= 12:
        return results[:24]

    for script in soup.find_all("script"):
        text = script.string or ""
        if "listResults" not in text and "searchResults" not in text:
            continue
        for match in re.finditer(
            r"\{[^{}]*\"zpid\"\s*:\s*\"?\d+\"?[^{}]*\"detailUrl\"\s*:\s*\"([^\"]+)\"[^{}]*\}",
            text,
        ):
            detail_path = match.group(1).replace("\\/", "/")
            listing_url = urljoin(base_url, detail_path)
            if listing_url in seen_urls:
                continue
            seen_urls.add(listing_url)
            chunk = match.group(0)
            title_match = re.search(r"\"address\"\s*:\s*\"([^\"]+)\"", chunk)
            price_match = re.search(r"\"price\"\s*:\s*(\d+)", chunk)
            beds_match = re.search(r"\"beds\"\s*:\s*(\d+)", chunk)
            baths_match = re.search(r"\"baths\"\s*:\s*([\d.]+)", chunk)
            photo_match = re.search(r"\"photo\"\s*:\s*\"([^\"]+)\"", chunk)
            photos = normalize_photo_list(
                [photo_match.group(1).replace("\\/", "/")],
                "zillow.com",
                limit=3,
            ) if photo_match else []
            results.append(
                {
                    "title": (title_match.group(1) if title_match else "Zillow rental"),
                    "url": listing_url,
                    "rent": float(price_match.group(1)) if price_match else None,
                    "bedrooms": float(beds_match.group(1)) if beds_match else None,
                    "bathrooms": float(baths_match.group(1)) if baths_match else None,
                    "snippet": "",
                    "photos": photos,
                }
            )

    for card in soup.select(
        "article[data-test='property-card'], .property-card, .list-card"
    ):
        link = card.select_one("a[href*='/homedetails/'], a[href*='/b/']")
        if not link:
            continue
        listing_url = urljoin(base_url, link.get("href", ""))
        if listing_url in seen_urls:
            continue
        seen_urls.add(listing_url)
        text = card.get_text(" ", strip=True)
        photos = []
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http"):
                photos = normalize_photo_list([src], "zillow.com", limit=3)
        results.append(
            {
                "title": link.get_text(strip=True) or "Zillow rental",
                "url": listing_url,
                "rent": _parse_price(text),
                "snippet": text[:300],
                "photos": photos,
                "bedrooms": None,
                "bathrooms": None,
            }
        )

    for match in ZILLOW_HOMEDETAILS_RE.findall(html):
        if match in seen_urls:
            continue
        seen_urls.add(match)
        slug_title = match.rstrip("/").split("/")[-1].replace("-", " ").title()
        results.append(
            {
                "title": slug_title[:200],
                "url": match,
                "rent": None,
                "snippet": "",
                "photos": [],
                "bedrooms": None,
                "bathrooms": None,
            }
        )

    return results[:24]

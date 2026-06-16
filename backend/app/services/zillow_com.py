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

    for script in soup.find_all("script", id="__NEXT_DATA__"):
        try:
            data = json.loads(script.string or "{}")
            queries = (
                data.get("props", {})
                .get("pageProps", {})
                .get("searchPageState", {})
                .get("cat1", {})
                .get("searchResults", {})
                .get("listResults", [])
            )
            for item in queries:
                if not isinstance(item, dict):
                    continue
                detail = item.get("detailUrl") or item.get("hdpUrl")
                if not detail:
                    continue
                listing_url = urljoin(base_url, str(detail))
                if listing_url in seen_urls:
                    continue
                seen_urls.add(listing_url)
                photos = normalize_photo_list(
                    [str(item["imgSrc"])] if item.get("imgSrc") else [],
                    "zillow.com",
                    limit=3,
                )
                results.append(
                    {
                        "title": str(item.get("address") or item.get("statusText") or "Zillow rental"),
                        "url": listing_url,
                        "rent": item.get("price") or _parse_price(str(item.get("unformattedPrice", ""))),
                        "bedrooms": item.get("beds"),
                        "bathrooms": item.get("baths"),
                        "snippet": str(item.get("info", ""))[:300],
                        "photos": photos,
                    }
                )
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

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

    return results[:12]

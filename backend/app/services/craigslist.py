"""Parse Craigslist listing pages and search thumbnails."""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list
from app.services.listing_fetcher import BROWSER_HEADERS

CRAIGSLIST_IMAGE_ID_RE = re.compile(
    r"images\d*\.craigslist\.org/([A-Za-z0-9_]+)_\d+x\d+[a-z]?\.(?:jpg|jpeg|png|webp)",
    re.I,
)

MAX_COVER_PHOTO_FETCHES = 20
COVER_PHOTO_WORKERS = 6


def _craigslist_gallery_url(image_id: str) -> str:
    return f"https://images.craigslist.org/{image_id}_600x450.jpg"


def fetch_craigslist_cover_photo(
    url: str, timeout: float = 12.0
) -> list[str]:
    """Fetch a single cover photo from a Craigslist listing detail page."""
    try:
        with httpx.Client(
            headers=BROWSER_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception:
        return []

    soup = BeautifulSoup(html[:100_000], "lxml")
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return normalize_photo_list([str(og_image["content"])], "craigslist", limit=1)

    for match in CRAIGSLIST_IMAGE_ID_RE.finditer(html):
        return normalize_photo_list(
            [_craigslist_gallery_url(match.group(1))],
            "craigslist",
            limit=1,
        )
    return []


def enrich_craigslist_results_with_cover_photos(
    results: list,
    *,
    max_fetches: int = MAX_COVER_PHOTO_FETCHES,
) -> None:
    """Attach cover photos to Craigslist search hits (search HTML has no thumbnails)."""
    to_fetch = [
        result
        for result in results
        if not result.photos and result.url and "craigslist.org" in result.url
    ][:max_fetches]
    if not to_fetch:
        return

    with ThreadPoolExecutor(max_workers=COVER_PHOTO_WORKERS) as pool:
        future_map = {
            pool.submit(fetch_craigslist_cover_photo, result.url): result
            for result in to_fetch
        }
        for future in as_completed(future_map):
            result = future_map[future]
            try:
                photos = future.result()
            except Exception:
                photos = []
            if photos:
                result.photos = photos


def parse_craigslist_listing(html: str, url: str) -> dict:
    """Parse a Craigslist listing detail page, preferring full gallery photos."""
    soup = BeautifulSoup(html, "lxml")
    out: dict = {
        "title": "",
        "photos": [],
        "phone": "",
        "email": "",
        "description": "",
        "address": "",
    }

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        out["title"] = og_title["content"]
    elif soup.title:
        out["title"] = soup.title.get_text(strip=True)

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        out["description"] = og_desc["content"]

    posting_title = soup.select_one("#postingtitletext, .postingtitletext")
    if posting_title:
        out["title"] = posting_title.get_text(" ", strip=True)

    body = soup.select_one("#postingbody")
    if body:
        out["description"] = body.get_text("\n", strip=True)[:4000]

    map_addr = soup.select_one(".mapaddress")
    if map_addr:
        out["address"] = map_addr.get_text(strip=True)

    image_ids: list[str] = []
    seen_ids: set[str] = set()
    for match in CRAIGSLIST_IMAGE_ID_RE.finditer(html):
        image_id = match.group(1)
        if image_id in seen_ids:
            continue
        seen_ids.add(image_id)
        image_ids.append(image_id)

    out["photos"] = normalize_photo_list(
        [_craigslist_gallery_url(image_id) for image_id in image_ids],
        "craigslist",
        limit=25,
    )
    return out

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def photo_request_headers(image_url: str, source_site: str = "") -> dict[str, str]:
    headers = {
        **BROWSER_HEADERS,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }
    lower = image_url.lower()
    site = (source_site or "").lower()
    if "apartments.com" in lower or site == "apartments.com":
        headers["Referer"] = "https://www.apartments.com/"
    elif "rent.com" in lower or "rentcafe.com" in lower or site == "rent.com":
        headers["Referer"] = "https://www.rent.com/"
    elif "craigslist.org" in lower or site == "craigslist":
        headers["Referer"] = "https://www.craigslist.org/"
    return headers

SKIP_IMAGE_PATTERNS = (
    "logo",
    "icon",
    "sprite",
    "avatar",
    "badge",
    "1x1",
    "pixel",
    "tracking",
    "placeholder.svg",
)

MIN_IMAGE_SIZE_HINT = 120

from app.services.image_quality import normalize_photo_list


@dataclass
class FetchedListing:
    url: str
    title: str = ""
    description: str = ""
    photos: list[str] = field(default_factory=list)
    source_site: str = ""
    extra_text: str = ""
    landlord_name: str = ""
    landlord_phone: str = ""
    landlord_email: str = ""
    contact_url: str = ""


def detect_source_site(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "apartments.com" in host:
        return "apartments.com"
    if "zillow.com" in host:
        return "zillow.com"
    if "craigslist.org" in host:
        return "craigslist"
    if "realtor.com" in host:
        return "realtor.com"
    if "rent.com" in host:
        return "rent.com"
    if "facebook.com" in host or "fb.com" in host:
        return "facebook"
    return "other"


def _is_valid_image_url(url: str) -> bool:
    if not url or url.startswith("data:"):
        return False
    lower = url.lower()
    if any(p in lower for p in SKIP_IMAGE_PATTERNS):
        return False
    if "apartments.com" in lower and ("/img_" in lower or "/116/" in lower or ".jpg" in lower):
        return True
    if "craigslist.org" in lower and "images.craigslist.org" in lower:
        return True
    return lower.endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".gif")
    ) or "image" in lower or "photo" in lower or "/img" in lower


def _normalize_url(base: str, src: str) -> Optional[str]:
    if not src:
        return None
    src = src.strip()
    if src.startswith("//"):
        src = "https:" + src
    if not src.startswith("http"):
        src = urljoin(base, src)
    if _is_valid_image_url(src):
        return src
    return None


def _extract_meta_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    photos: list[str] = []
    meta_keys = [
        ("property", "og:image"),
        ("name", "og:image"),
        ("property", "og:image:url"),
        ("name", "twitter:image"),
        ("property", "twitter:image"),
    ]
    for attr, key in meta_keys:
        for tag in soup.find_all("meta", {attr: key}):
            content = tag.get("content")
            normalized = _normalize_url(base_url, content or "")
            if normalized and normalized not in photos:
                photos.append(normalized)

    for tag in soup.find_all("link", rel=lambda r: r and "image_src" in r):
        normalized = _normalize_url(base_url, tag.get("href", ""))
        if normalized and normalized not in photos:
            photos.append(normalized)
    return photos


def _extract_img_tags(soup: BeautifulSoup, base_url: str) -> list[str]:
    photos: list[str] = []
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-image"):
            normalized = _normalize_url(base_url, img.get(attr, "") or "")
            if normalized and normalized not in photos:
                width = img.get("width")
                if width and str(width).isdigit() and int(width) < MIN_IMAGE_SIZE_HINT:
                    continue
                photos.append(normalized)
    return photos


def _extract_json_ld_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    photos: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            image = item.get("image")
            if isinstance(image, str):
                normalized = _normalize_url(base_url, image)
                if normalized:
                    photos.append(normalized)
            elif isinstance(image, list):
                for img in image:
                    if isinstance(img, str):
                        normalized = _normalize_url(base_url, img)
                        if normalized:
                            photos.append(normalized)
                    elif isinstance(img, dict) and img.get("url"):
                        normalized = _normalize_url(base_url, img["url"])
                        if normalized:
                            photos.append(normalized)
    return photos


def _extract_site_gallery(soup: BeautifulSoup, base_url: str, site: str) -> list[str]:
    photos: list[str] = []
    selectors = {
        "apartments.com": [
            "img.carouselPhoto",
            ".mediaGallery img",
            ".aspectRatioImage img",
            "[class*='gallery'] img",
            ".placard img",
        ],
        "zillow.com": [
            "[data-testid='media-stream'] img",
            ".media-stream img",
            "ul.photo-carousel img",
        ],
        "craigslist": [
            ".gallery img",
            "#thumbs img",
            ".slide img",
        ],
        "realtor.com": [
            "[data-testid='hero-image'] img",
            ".photo-carousel img",
        ],
        "rent.com": [
            "[data-testid='gallery'] img",
            "[class*='Gallery'] img",
            "[class*='carousel'] img",
            "img[src*='i.rent.com']",
        ],
    }
    for selector in selectors.get(site, []):
        for img in soup.select(selector):
            for attr in ("src", "data-src", "data-lazy", "data-original"):
                normalized = _normalize_url(base_url, img.get(attr, "") or "")
                if normalized and normalized not in photos:
                    photos.append(normalized)
    return photos


def _page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
    og_desc = soup.find("meta", property="og:description")
    description = og_desc.get("content", "") if og_desc else ""
    body = soup.get_text(separator="\n", strip=True)
    combined = "\n".join(filter(None, [title, description, body[:8000]]))
    return combined[:12000]


def fetch_listing_from_url(url: str, timeout: float = 20.0) -> FetchedListing:
    site = detect_source_site(url)
    if site == "apartments.com":
        from app.services.apartments_com import canonicalize_apartments_com_listing_url

        url = canonicalize_apartments_com_listing_url(url)
    result = FetchedListing(url=url, source_site=site)

    try:
        with httpx.Client(
            headers=BROWSER_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)
    except Exception as exc:
        result.extra_text = f"Could not fetch listing page: {exc}"
        return result

    soup = BeautifulSoup(html, "lxml")
    result.url = final_url
    result.source_site = detect_source_site(final_url)

    parsed_site_data: Optional[dict] = None

    if result.source_site == "apartments.com":
        from app.services.apartments_com import parse_apartments_com_listing

        parsed_site_data = parse_apartments_com_listing(html, final_url)
    elif result.source_site == "rent.com":
        from app.services.rent_com import parse_rent_com_listing

        parsed_site_data = parse_rent_com_listing(html, final_url)
    elif result.source_site == "craigslist":
        from app.services.craigslist import parse_craigslist_listing

        parsed_site_data = parse_craigslist_listing(html, final_url)

    if parsed_site_data:
        if parsed_site_data.get("title"):
            result.title = parsed_site_data["title"]
        if parsed_site_data.get("photos"):
            result.photos = parsed_site_data["photos"]
        if parsed_site_data.get("phone"):
            result.landlord_phone = parsed_site_data["phone"]
        if parsed_site_data.get("email"):
            result.landlord_email = parsed_site_data["email"]
        if parsed_site_data.get("contact_name"):
            result.landlord_name = parsed_site_data["contact_name"]
        if parsed_site_data.get("description"):
            result.description = parsed_site_data["description"]
        if parsed_site_data.get("address"):
            result.extra_text = f"Address: {parsed_site_data['address']}"
        result.contact_url = parsed_site_data.get("contact_url") or final_url

    seen: set[str] = set(result.photos)
    if result.source_site != "craigslist":
        for extractor in (
            _extract_meta_images,
            _extract_json_ld_images,
            lambda s, b: _extract_site_gallery(s, b, result.source_site),
            _extract_img_tags,
        ):
            for photo in extractor(soup, final_url):
                if photo not in seen:
                    seen.add(photo)
                    result.photos.append(photo)

    result.photos = normalize_photo_list(
        result.photos, result.source_site, limit=25
    )

    if not result.title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            result.title = og_title["content"]
        elif soup.title:
            result.title = soup.title.get_text(strip=True)

    if not result.description:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            result.description = og_desc["content"]
        else:
            result.description = _page_text(soup)[:4000]

    if not result.extra_text:
        summary_parts = [result.description[:2000]]
        if parsed_site_data and parsed_site_data.get("address"):
            summary_parts.insert(0, f"Address: {parsed_site_data['address']}")
        result.extra_text = "\n".join(summary_parts)
    return result


def enrich_listing_text(raw_text: str, fetched: FetchedListing) -> str:
    parts = [raw_text.strip()]
    if fetched.title and fetched.title not in raw_text:
        parts.append(f"Title: {fetched.title}")
    if fetched.description and len(fetched.description) < 3000:
        parts.append(fetched.description)
    elif fetched.extra_text and len(raw_text) < 800:
        parts.append(fetched.extra_text[:2500])
    if fetched.photos:
        parts.append(f"Photos available: {len(fetched.photos)} images from listing page")
    if fetched.landlord_phone:
        parts.append(f"Landlord phone: {fetched.landlord_phone}")
    if fetched.landlord_email:
        parts.append(f"Landlord email: {fetched.landlord_email}")
    if fetched.landlord_name:
        parts.append(f"Property contact: {fetched.landlord_name}")
    return "\n\n".join(parts)[:10000]


def fetched_to_landlord_contact(fetched: FetchedListing) -> dict:
    return {
        "name": fetched.landlord_name or None,
        "phone": fetched.landlord_phone or None,
        "email": fetched.landlord_email or None,
        "contact_url": fetched.contact_url or fetched.url or None,
    }

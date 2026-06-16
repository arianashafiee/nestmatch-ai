import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list

APARTMENTS_COM_IMAGE_RE = re.compile(
    r"https://images\d*\.apartments\.com/[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)",
    re.I,
)

# Single listing pages: .../property-slug-city-st/{6-7 char id}/ or legacy numeric id
APARTMENTS_COM_LISTING_RE = re.compile(
    r"https://www\.apartments\.com/[^\s\"'<>]+/[a-z0-9]{6,8}/?",
    re.I,
)

APARTMENTS_COM_LISTING_LEGACY_RE = re.compile(
    r"https://www\.apartments\.com/[^\s\"'<>]+/\d{5,}/?",
    re.I,
)

APARTMENTS_COM_DETAIL_ID_RE = re.compile(r"^[a-z0-9]{6,16}$", re.I)
APARTMENTS_COM_DETAIL_ID_LEGACY_RE = re.compile(r"^\d{5,}$")

APARTMENTS_COM_SEARCH_SEGMENT_MARKERS = (
    "under-",
    "bedrooms",
    "bedroom",
    "min-",
    "pet-friendly",
    "luxury",
    "cheap",
    "short-term",
    "studio",
    "houses",
    "townhomes",
    "condos",
)


def is_apartments_com_listing_url(url: str) -> bool:
    """True for a single-property detail page, not search/filter pages."""
    parsed = urlparse(url)
    if "apartments.com" not in parsed.netloc.lower():
        return False
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return False

    listing_id = parts[-1]
    if not (
        APARTMENTS_COM_DETAIL_ID_RE.match(listing_id)
        or APARTMENTS_COM_DETAIL_ID_LEGACY_RE.match(listing_id)
    ):
        return False

    slug = parts[-2]
    if slug in ("apartments", "houses", "townhomes", "condos") and len(parts) >= 3:
        return True
    if slug in ("apartments", "houses", "townhomes", "condos"):
        return False
    if any(marker in slug for marker in APARTMENTS_COM_SEARCH_SEGMENT_MARKERS):
        return False
    if any(marker in listing_id for marker in APARTMENTS_COM_SEARCH_SEGMENT_MARKERS):
        return False
    return True


def canonicalize_apartments_com_listing_url(url: str) -> str:
    """Strip tracking query/hash and normalize to a single listing detail URL."""
    parsed = urlparse(url.strip())
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return url.strip()

    if len(parts) >= 2 and (
        APARTMENTS_COM_DETAIL_ID_RE.match(parts[-1])
        or APARTMENTS_COM_DETAIL_ID_LEGACY_RE.match(parts[-1])
    ):
        listing_id = parts[-1]
        slug = parts[-2]
        slug = re.sub(r"-[a-z]{2}-\d+$", "", slug, flags=re.I)
        slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
        slug = re.sub(r"-+", "-", slug)
        parts = [slug, listing_id]

    clean_path = "/" + "/".join(parts) + "/"
    host = parsed.netloc.lower() or "www.apartments.com"
    if "apartments.com" not in host:
        host = "www.apartments.com"
    return urlunparse((parsed.scheme or "https", host, clean_path, "", "", ""))


def _clean_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw)
    return raw.strip() if len(digits) >= 10 else ""


def _photos_from_srcset(value: str) -> list[str]:
    urls: list[str] = []
    for part in value.split(","):
        src = part.strip().split(" ")[0]
        if src.startswith("http"):
            urls.append(src)
    return urls


def parse_apartments_com_search(html: str, base_url: str) -> list[dict]:
    """Parse apartments.com search results page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen: set[str] = set()

    for card in soup.select(
        "article.placard, li.mortar-wrapper, [data-listingid], .property-wrapper"
    ):
        link = card.select_one(
            "a.property-link[href], a[href*='apartments.com'][href]"
        )
        if not link:
            continue
        href = link.get("href", "")
        if not href:
            continue
        listing_url = canonicalize_apartments_com_listing_url(urljoin(base_url, href))
        if listing_url in seen:
            continue
        if "apartments.com" not in listing_url or not is_apartments_com_listing_url(
            listing_url
        ):
            continue
        seen.add(listing_url)

        title_el = card.select_one(
            ".property-title, .js-placardTitle, .property-title-wrapper, span.title"
        )
        title = (title_el or link).get_text(strip=True)
        price_el = card.select_one(
            ".property-pricing, .rent, .price-range, [class*='rent']"
        )
        price_text = (
            price_el.get_text(" ", strip=True) if price_el else card.get_text(" ", strip=True)
        )
        photos = normalize_photo_list(
            _extract_apartments_com_images_from_element(card, base_url),
            "apartments.com",
            limit=5,
        )
        if not photos:
            photos = normalize_photo_list(
                _extract_apartments_com_images_from_html(str(card)),
                "apartments.com",
                limit=5,
            )

        results.append(
            {
                "title": title[:200],
                "url": listing_url,
                "snippet": price_text[:300],
                "photos": photos,
                "rent": _parse_rent(price_text),
            }
        )

    if len(results) < 3:
        results.extend(_parse_apartments_com_search_json_ld(html, seen))

    if len(results) < 3:
        for match in APARTMENTS_COM_LISTING_RE.findall(html):
            listing_url = canonicalize_apartments_com_listing_url(match)
            if listing_url in seen or not is_apartments_com_listing_url(listing_url):
                continue
            seen.add(listing_url)
            slug_title = listing_url.rstrip("/").split("/")[-2].replace("-", " ").title()
            results.append(
                {
                    "title": slug_title[:200],
                    "url": listing_url,
                    "snippet": "",
                    "photos": normalize_photo_list(
                        _extract_apartments_com_images_near(html, listing_url),
                        "apartments.com",
                        limit=5,
                    ),
                    "rent": None,
                }
            )
        for match in APARTMENTS_COM_LISTING_LEGACY_RE.findall(html):
            listing_url = canonicalize_apartments_com_listing_url(match)
            if listing_url in seen or not is_apartments_com_listing_url(listing_url):
                continue
            seen.add(listing_url)
            slug_title = listing_url.rstrip("/").split("/")[-2].replace("-", " ").title()
            results.append(
                {
                    "title": slug_title[:200],
                    "url": listing_url,
                    "snippet": "",
                    "photos": normalize_photo_list(
                        _extract_apartments_com_images_near(html, listing_url),
                        "apartments.com",
                        limit=5,
                    ),
                    "rent": None,
                }
            )

    return results[:12]


def _parse_apartments_com_search_json_ld(html: str, seen: set[str]) -> list[dict]:
    """Extract listing URLs from embedded JSON-LD on search pages."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        graph = data.get("@graph") if isinstance(data, dict) else None
        items = graph if isinstance(graph, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            entity_type = item.get("@type") or ""
            if isinstance(entity_type, list):
                entity_type = " ".join(entity_type)
            if "ApartmentComplex" not in str(entity_type):
                continue
            raw_id = str(item.get("@id") or item.get("url") or "")
            listing_url = canonicalize_apartments_com_listing_url(
                raw_id.split("#")[0]
            )
            if listing_url in seen or not is_apartments_com_listing_url(listing_url):
                continue
            seen.add(listing_url)
            title = str(item.get("name") or "").strip()
            if not title:
                title = listing_url.rstrip("/").split("/")[-2].replace("-", " ").title()
            rent = None
            offers = item.get("offers")
            if isinstance(offers, dict):
                low = offers.get("lowPrice") or offers.get("price")
                if low is not None:
                    try:
                        rent = float(str(low).replace(",", "").replace("$", ""))
                    except ValueError:
                        rent = None
            photos: list[str] = []
            image = item.get("image")
            if isinstance(image, str):
                photos = [image]
            elif isinstance(image, list):
                photos = [str(img) for img in image if isinstance(img, str)]
            results.append(
                {
                    "title": title[:200],
                    "url": listing_url,
                    "snippet": "",
                    "photos": normalize_photo_list(
                        photos, "apartments.com", limit=5
                    ),
                    "rent": rent,
                }
            )
    return results


def parse_apartments_com_listing(html: str, url: str) -> dict:
    """Parse a single apartments.com listing detail page."""
    soup = BeautifulSoup(html, "lxml")
    out: dict = {
        "title": "",
        "photos": [],
        "phone": "",
        "email": "",
        "contact_name": "",
        "contact_url": url,
        "description": "",
        "address": "",
    }

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        out["title"] = og_title["content"]
    elif soup.title:
        out["title"] = soup.title.get_text(strip=True)

    photo_urls: list[str] = []

    # Embedded gallery JSON often has full-size URLs
    for script in soup.find_all("script"):
        text = script.string or ""
        if "apartments.com" not in text or "photo" not in text.lower():
            continue
        photo_urls.extend(APARTMENTS_COM_IMAGE_RE.findall(text))

    photo_urls.extend(_extract_apartments_com_images_from_html(html))
    for img in soup.select(
        "img.carouselPhoto, .mediaGallery img, .aspectRatioImage img, "
        "[class*='gallery'] img, [data-image], picture source"
    ):
        for attr in ("src", "data-src", "srcset", "data-image", "content", "data-srcset"):
            val = img.get(attr, "") or ""
            if attr == "srcset":
                photo_urls.extend(_photos_from_srcset(val))
            else:
                for part in val.split(","):
                    src = part.strip().split(" ")[0]
                    if "apartments.com" in src:
                        photo_urls.append(src)

    out["photos"] = normalize_photo_list(photo_urls, "apartments.com", limit=25)

    for a in soup.select('a[href^="tel:"]'):
        phone = _clean_phone(a.get("href", "").replace("tel:", ""))
        if phone:
            out["phone"] = phone
            break
    for a in soup.select('a[href^="mailto:"]'):
        email = a.get("href", "").replace("mailto:", "").split("?")[0].strip()
        if email and "@" in email:
            out["email"] = email
            break

    for sel in (
        ".phoneNumber",
        ".propertyPhone",
        "[class*='leasing'] [class*='phone']",
        ".contactInfo",
        ".propertyInformation .phone",
    ):
        el = soup.select_one(sel)
        if el:
            phone = _clean_phone(el.get_text(strip=True))
            if phone:
                out["phone"] = phone
                break

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if not out["title"] and item.get("name"):
                out["title"] = str(item["name"])
            if item.get("telephone") and not out["phone"]:
                out["phone"] = _clean_phone(str(item["telephone"]))
            addr = item.get("address")
            if isinstance(addr, dict) and not out["address"]:
                parts = [
                    addr.get("streetAddress"),
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("postalCode"),
                ]
                out["address"] = ", ".join(p for p in parts if p)
            seller = item.get("seller") or item.get("brand")
            if isinstance(seller, dict):
                if seller.get("name") and not out["contact_name"]:
                    out["contact_name"] = str(seller["name"])
                if seller.get("telephone") and not out["phone"]:
                    out["phone"] = _clean_phone(str(seller["telephone"]))
            image = item.get("image")
            if isinstance(image, str):
                photo_urls.append(image)
            elif isinstance(image, list):
                for img in image:
                    if isinstance(img, str):
                        photo_urls.append(img)
                    elif isinstance(img, dict) and img.get("url"):
                        photo_urls.append(str(img["url"]))
    out["photos"] = normalize_photo_list(photo_urls, "apartments.com", limit=25)

    if not out["phone"]:
        phone_match = re.search(
            r'"phone(?:Number)?"\s*:\s*"([^"]+)"', html, re.I
        )
        if phone_match:
            out["phone"] = _clean_phone(phone_match.group(1))

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        out["description"] = og_desc["content"]

    return out


def _extract_apartments_com_images_from_html(html: str) -> list[str]:
    return APARTMENTS_COM_IMAGE_RE.findall(html)


def _extract_apartments_com_images_from_element(el, base_url: str) -> list[str]:
    photos: list[str] = []
    for img in el.select("img"):
        for attr in ("src", "data-src", "data-image", "data-original", "srcset"):
            val = img.get(attr, "") or ""
            if attr == "srcset":
                photos.extend(_photos_from_srcset(val))
            elif "apartments.com" in val:
                photos.append(val)
    return photos


def _extract_apartments_com_images_near(html: str, url: str) -> list[str]:
    idx = html.find(url)
    if idx == -1:
        return []
    chunk = html[max(0, idx - 2000) : idx + 2000]
    return _extract_apartments_com_images_from_html(chunk)[:3]


def _parse_rent(text: str) -> Optional[float]:
    match = re.search(r"\$[\d,]+", text)
    if match:
        return float(match.group().replace("$", "").replace(",", ""))
    return None

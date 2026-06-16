import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Apartments.com: .../img_HASH/WIDTH/file.jpg — 116/117 are thumbnails
APARTMENTS_COM_SIZE_RE = re.compile(
    r"(https://images\d*\.apartments\.com/img_[a-f0-9]+)/\d+/",
    re.I,
)

APARTMENTS_COM_MAX_IMAGE_WIDTH = 1280

# Rent.com: t_3x2_fixed_webp_md -> xl (largest common variant)
RENT_COM_SIZE_RE = re.compile(
    r"(t_(?:3x2_fixed|w)_webp_)(?:md|sm|w720|w1440|lg)(/[\w-]+)",
    re.I,
)

# Cloudinary / RentCafe: bump width in transform chain
RENTCAFE_WIDTH_RE = re.compile(r"w_\d+")
RENTCAFE_WIDTH_RE2 = re.compile(r",w_\d+,")


def upgrade_apartments_com_image(url: str) -> str:
    if "apartments.com" not in url.lower():
        return url
    max_w = str(APARTMENTS_COM_MAX_IMAGE_WIDTH)
    upgraded = APARTMENTS_COM_SIZE_RE.sub(rf"\1/{max_w}/", url)
    parsed = urlparse(upgraded)
    if parsed.query:
        params = parse_qs(parsed.query)
        for key in ("w", "width", "h", "height"):
            if key in params:
                params[key] = [max_w]
        upgraded = urlunparse(
            parsed._replace(query=urlencode(params, doseq=True))
        )
    return upgraded


def upgrade_rent_com_image(url: str) -> str:
    if "rent.com" not in url.lower() and "rentcafe.com" not in url.lower():
        return url
    if "i.rent.com" in url.lower():
        return RENT_COM_SIZE_RE.sub(r"\1xl\2", url)
    if "resource.rentcafe.com" in url.lower():
        upgraded = RENTCAFE_WIDTH_RE.sub("w_1920", url)
        upgraded = RENTCAFE_WIDTH_RE2.sub(",w_1920,", upgraded)
        return upgraded
    return url


def rent_com_photo_url(photo_id: str, variant: str = "xl") -> str:
    """Build a full-size rent.com CDN URL from a photo id."""
    clean_id = photo_id.strip().lstrip("/")
    return f"https://i.rent.com/t_3x2_fixed_webp_{variant}/{clean_id}"


def _image_dedupe_key(url: str) -> str:
    lower = url.lower()
    m = re.search(r"/img_([a-f0-9]+)/", lower)
    if m:
        return f"apartments:{m.group(1)}"
    m = re.search(r"/([\da-f]{20,})(?:\?|$)", lower)
    if m and "rent.com" in lower:
        return f"rent:{m.group(1)}"
    m = re.search(r"/s3/[\d/]+/([^/?]+)", lower)
    if m:
        return f"rentcafe:{m.group(1)}"
    return url


def normalize_photo_url(url: str, source_site: str = "") -> str:
    site = (source_site or "").lower()
    if "apartments.com" in url.lower() or site == "apartments.com":
        return upgrade_apartments_com_image(url)
    if "rent.com" in url.lower() or "rentcafe.com" in url.lower() or site == "rent.com":
        return upgrade_rent_com_image(url)
    return url


def normalize_photo_list(
    photos: list[str], source_site: str = "", limit: int = 25
) -> list[str]:
    """Upgrade resolution, dedupe by underlying image id, preserve order."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in photos:
        if not raw or not isinstance(raw, str):
            continue
        url = normalize_photo_url(raw.strip(), source_site)
        key = _image_dedupe_key(url)
        if key in seen:
            continue
        seen.add(key)
        out.append(url)
        if len(out) >= limit:
            break
    return out

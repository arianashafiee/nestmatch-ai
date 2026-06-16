import re

from bs4 import BeautifulSoup

from app.services.image_quality import normalize_photo_list

CRAIGSLIST_IMAGE_ID_RE = re.compile(
    r"images\d*\.craigslist\.org/([A-Za-z0-9_]+)_\d+x\d+[a-z]?\.(?:jpg|jpeg|png|webp)",
    re.I,
)


def _craigslist_gallery_url(image_id: str) -> str:
    return f"https://images.craigslist.org/{image_id}_600x450.jpg"


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

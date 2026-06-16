from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.image_quality import normalize_photo_url
from app.services.listing_fetcher import detect_source_site, photo_request_headers

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/proxy")
def proxy_photo(url: str = Query(..., min_length=10)) -> Response:
    target = unquote(url)
    if not target.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    site = detect_source_site(target)
    target = normalize_photo_url(target, site)
    headers = photo_request_headers(target, site)

    try:
        with httpx.Client(
            headers=headers,
            timeout=15,
            follow_redirects=True,
        ) as client:
            response = client.get(target)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/jpeg")
            if "image" not in content_type:
                content_type = "image/jpeg"
            return Response(
                content=response.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load image: {exc}",
        ) from exc

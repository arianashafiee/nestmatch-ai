from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.listing_fetcher import fetch_proxied_photo

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/proxy")
def proxy_photo(url: str = Query(..., min_length=10)) -> Response:
    target = unquote(url)
    if not target.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    try:
        content, content_type = fetch_proxied_photo(target)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load image: {exc}",
        ) from exc

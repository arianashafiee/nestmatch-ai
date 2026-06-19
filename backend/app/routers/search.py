from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.routers.profile import get_profile_for_user
from app.schemas import SearchListingItem, SearchListingsRequest, SearchListingsResponse
from app.services.image_quality import normalize_photo_list
from app.services.listing_search import search_all_sources, search_result_to_raw_text

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search-listings", response_model=SearchListingsResponse)
def search_listings(
    payload: SearchListingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchListingsResponse:
    try:
        profile = get_profile_for_user(db, current_user)

        if not profile.campus_location and not profile.university:
            raise HTTPException(
                status_code=400,
                detail="Complete your profile with a campus location first.",
            )

        data = search_all_sources(profile)
        items = [
            SearchListingItem(
                title=r.title,
                url=r.url,
                source_site=r.source_site,
                rent=r.rent,
                bedrooms=r.bedrooms,
                bathrooms=r.bathrooms,
                snippet=r.snippet,
                photos=normalize_photo_list(
                    r.photos or [],
                    r.source_site or "",
                    limit=5,
                ),
                location=r.location,
                listing_address=r.listing_address,
                distance_miles=r.distance_miles,
                commute_minutes=r.commute_minutes,
                raw_text=search_result_to_raw_text(r),
            )
            for r in data["results"]
        ]

        return SearchListingsResponse(
            results=items,
            sources_searched=data["sources_searched"],
            errors=data["errors"],
            location=data["location"],
            search_area=data.get("search_area", ""),
            max_rent=data["max_rent"],
            campus_geocoded=data.get("campus_geocoded", False),
            max_commute_minutes=data.get("max_commute_minutes", 30),
            commute_mode=data.get("commute_mode", "walking"),
            ai_ranked=data.get("ai_ranked", False),
            ai_discovered=data.get("ai_discovered", False),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {exc}",
        ) from exc

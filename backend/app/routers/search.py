from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentProfile
from app.routers.profile import get_or_create_profile
from app.schemas import SearchListingItem, SearchListingsRequest, SearchListingsResponse
from app.services.listing_search import search_all_sources, search_result_to_raw_text

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search-listings", response_model=SearchListingsResponse)
def search_listings(
    payload: SearchListingsRequest,
    db: Session = Depends(get_db),
) -> SearchListingsResponse:
    try:
        profile = db.get(StudentProfile, payload.profile_id)
        if profile is None:
            profile = get_or_create_profile(db)

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
                photos=r.photos,
                location=r.location,
                raw_text=search_result_to_raw_text(r),
            )
            for r in data["results"]
        ]

        return SearchListingsResponse(
            results=items,
            sources_searched=data["sources_searched"],
            errors=data["errors"],
            location=data["location"],
            max_rent=data["max_rent"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {exc}",
        ) from exc

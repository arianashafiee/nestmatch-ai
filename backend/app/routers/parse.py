from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApartmentListing, StudentProfile
from app.routers.profile import get_or_create_profile
from app.schemas import ParseListingRequest, ParseListingResponse
from app.services.listing_hydrate import extract_url_from_text, hydrate_listing_from_url
from app.services.llm_parser import parse_listing

MAX_PARSE_TEXT = 10000


def _prepare_listing_text(text: str) -> str:
    """Keep parse input bounded — scraped pages can be huge and break analysis."""
    cleaned = text.strip()
    if len(cleaned) <= MAX_PARSE_TEXT:
        return cleaned
    url = extract_url_from_text(cleaned)
    if url:
        head = cleaned[:4000]
        tail = cleaned[-1500:]
        return f"{head}\n\n[... trimmed for analysis ...]\n\n{tail}"[:MAX_PARSE_TEXT]
    return cleaned[:MAX_PARSE_TEXT]

router = APIRouter(prefix="/api", tags=["parse"])


@router.post("/parse-listing", response_model=ParseListingResponse)
def parse_listing_endpoint(
    payload: ParseListingRequest,
    db: Session = Depends(get_db),
) -> ParseListingResponse:
    try:
        profile = db.get(StudentProfile, payload.profile_id)
        if profile is None:
            profile = get_or_create_profile(db)

        listing_text = _prepare_listing_text(
            payload.listing_text.strip() if not payload.apartment_id else ""
        )
        apartment: Optional[ApartmentListing] = None

        if payload.apartment_id:
            apartment = db.get(ApartmentListing, payload.apartment_id)
            if apartment is None:
                raise HTTPException(status_code=404, detail="Apartment not found")
            listing_text = _prepare_listing_text(apartment.raw_text)

        source_url = None
        if apartment:
            source_url = apartment.source_url
        else:
            source_url = extract_url_from_text(listing_text)

        if apartment is None:
            apartment = ApartmentListing(
                profile_id=payload.profile_id,
                raw_text=listing_text,
                source_url=source_url,
                status="interested",
            )
            db.add(apartment)
        else:
            apartment.status = "interested"

        if source_url:
            listing_text = hydrate_listing_from_url(
                apartment,
                listing_text,
                source_url,
                fetch_photos=True,
            )
            apartment.raw_text = listing_text

        photo_count = len(apartment.photos or [])
        analysis, parsed_with = parse_listing(
            listing_text, profile, photo_count=photo_count
        )
        now = datetime.now(timezone.utc)

        apartment.title = analysis.title
        apartment.compatibility_score = analysis.compatibility_score
        apartment.analysis = analysis.model_dump()
        apartment.parsed_at = now

        db.commit()
        db.refresh(apartment)

        return ParseListingResponse(
            id=apartment.id,
            profile_id=apartment.profile_id,
            raw_text=apartment.raw_text,
            source_url=apartment.source_url,
            status=apartment.status,
            title=apartment.title,
            compatibility_score=apartment.compatibility_score,
            analysis=analysis,
            photos=apartment.photos or [],
            source_site=apartment.source_site,
            landlord_contact=apartment.landlord_contact,
            parsed_at=apartment.parsed_at,
            created_at=apartment.created_at,
            parsed_with=parsed_with,
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database error while saving parsed listing.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse listing: {exc}",
        ) from exc

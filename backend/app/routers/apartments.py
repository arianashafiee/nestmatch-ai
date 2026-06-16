from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApartmentListing
from app.routers.profile import DEFAULT_PROFILE_ID, get_or_create_profile
from app.schemas import (
    ApartmentDraftCreate,
    ApartmentResponse,
    ApartmentStatusUpdate,
)
from app.services.image_quality import normalize_photo_list
from app.services.listing_fetcher import detect_source_site
from app.services.listing_hydrate import extract_url_from_text, hydrate_listing_from_url

router = APIRouter(prefix="/api/apartments", tags=["apartments"])


@router.get("", response_model=list[ApartmentResponse])
def list_apartments(db: Session = Depends(get_db)) -> list[ApartmentListing]:
    try:
        get_or_create_profile(db)
        return (
            db.query(ApartmentListing)
            .filter(ApartmentListing.profile_id == DEFAULT_PROFILE_ID)
            .order_by(ApartmentListing.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@router.put("/{apartment_id}/status", response_model=ApartmentResponse)
def update_apartment_status(
    apartment_id: int,
    payload: ApartmentStatusUpdate,
    db: Session = Depends(get_db),
) -> ApartmentListing:
    try:
        listing = db.get(ApartmentListing, apartment_id)
        if listing is None:
            raise HTTPException(status_code=404, detail="Apartment not found")
        listing.status = payload.status
        db.commit()
        db.refresh(listing)
        return listing
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Could not update listing status.",
        ) from exc


@router.post("/{apartment_id}/refresh-photos", response_model=ApartmentResponse)
def refresh_listing_photos(
    apartment_id: int,
    db: Session = Depends(get_db),
) -> ApartmentListing:
    listing = db.get(ApartmentListing, apartment_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    if not listing.source_url:
        raise HTTPException(status_code=400, detail="No source URL to fetch photos from")

    try:
        enriched = hydrate_listing_from_url(
            listing,
            listing.raw_text,
            listing.source_url,
            fetch_photos=True,
        )
        if enriched != listing.raw_text:
            listing.raw_text = enriched
        db.commit()
        db.refresh(listing)
        return listing
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database error") from exc


@router.get("/{apartment_id}", response_model=ApartmentResponse)
def get_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
) -> ApartmentListing:
    listing = db.get(ApartmentListing, apartment_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return listing


@router.post("", response_model=ApartmentResponse, status_code=201)
def create_apartment_draft(
    payload: ApartmentDraftCreate,
    db: Session = Depends(get_db),
) -> ApartmentListing:
    try:
        get_or_create_profile(db)
        source_url = payload.source_url or extract_url_from_text(payload.raw_text)
        if source_url and detect_source_site(source_url) == "apartments.com":
            from app.services.apartments_com import canonicalize_apartments_com_listing_url

            source_url = canonicalize_apartments_com_listing_url(source_url)
        source_site = payload.source_site
        if source_url and not source_site:
            source_site = detect_source_site(source_url)
        initial_photos = (
            normalize_photo_list(payload.photos, source_site or "", limit=20)
            if payload.photos
            else []
        )
        listing = ApartmentListing(
            profile_id=DEFAULT_PROFILE_ID,
            raw_text=payload.raw_text.strip(),
            source_url=source_url,
            status="pending",
            photos=initial_photos,
            source_site=source_site,
        )

        if source_url and payload.fetch_photos:
            listing.raw_text = hydrate_listing_from_url(
                listing,
                listing.raw_text,
                source_url,
                fetch_photos=True,
            )
        elif source_url and not listing.source_site:
            listing.source_site = detect_source_site(source_url)

        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Could not save listing to the database.",
        ) from exc

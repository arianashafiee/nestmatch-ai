from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ApartmentListing, User
from app.routers.profile import get_profile_for_user
from app.schemas import (
    ApartmentDraftCreate,
    ApartmentResponse,
    ApartmentStatusUpdate,
)
from app.services.image_quality import normalize_photo_list
from app.services.listing_fetcher import detect_source_site
from app.services.listing_hydrate import extract_url_from_text, hydrate_listing_from_url

router = APIRouter(prefix="/api/apartments", tags=["apartments"])


def _get_user_listing(
    db: Session,
    apartment_id: int,
    current_user: User,
) -> ApartmentListing:
    profile = get_profile_for_user(db, current_user)
    listing = db.get(ApartmentListing, apartment_id)
    if listing is None or listing.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return listing


@router.get("", response_model=list[ApartmentResponse])
def list_apartments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApartmentListing]:
    try:
        profile = get_profile_for_user(db, current_user)
        return (
            db.query(ApartmentListing)
            .filter(ApartmentListing.profile_id == profile.id)
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
    current_user: User = Depends(get_current_user),
) -> ApartmentListing:
    try:
        listing = _get_user_listing(db, apartment_id, current_user)
        payload_data = payload.model_dump(exclude_unset=True)
        if not payload_data:
            raise HTTPException(status_code=400, detail="No updates provided")
        if payload_data.get("status") is not None:
            next_status = payload_data["status"]
            if next_status == "tour_scheduled":
                tour_at = (
                    payload_data["tour_at"]
                    if "tour_at" in payload_data
                    else listing.tour_at
                )
                if not tour_at:
                    raise HTTPException(
                        status_code=400,
                        detail="Set a tour date and time before moving to Tour Scheduled.",
                    )
            listing.status = next_status
        if payload_data.get("is_favorite") is not None:
            listing.is_favorite = payload_data["is_favorite"]
        if "tour_at" in payload_data:
            listing.tour_at = payload_data["tour_at"]
        if payload_data.get("tour_notes") is not None:
            listing.tour_notes = payload_data["tour_notes"]
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
    current_user: User = Depends(get_current_user),
) -> ApartmentListing:
    listing = _get_user_listing(db, apartment_id, current_user)
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


@router.delete("/{apartment_id}", status_code=204)
def delete_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        listing = _get_user_listing(db, apartment_id, current_user)
        db.delete(listing)
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Could not delete listing.",
        ) from exc


@router.get("/{apartment_id}", response_model=ApartmentResponse)
def get_apartment(
    apartment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApartmentListing:
    return _get_user_listing(db, apartment_id, current_user)


@router.post("", response_model=ApartmentResponse, status_code=201)
def create_apartment_draft(
    payload: ApartmentDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApartmentListing:
    try:
        profile = get_profile_for_user(db, current_user)
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
            profile_id=profile.id,
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
            if (
                not listing.photos
                and listing.source_site == "craigslist"
                and source_url
            ):
                from app.services.craigslist import fetch_craigslist_cover_photo

                cover = fetch_craigslist_cover_photo(source_url)
                if cover:
                    listing.photos = normalize_photo_list(
                        cover, "craigslist", limit=5
                    )
            if listing.photos:
                listing.photos = normalize_photo_list(
                    listing.photos,
                    listing.source_site or "",
                    limit=20,
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

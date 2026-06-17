from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.routers.profile import get_profile_for_user
from app.schemas import CommuteBatchRequest, CommuteBatchResponse, CommuteEstimate
from app.services.geo import (
    commute_between_coords,
    geocode,
    mapbox_batch_route_commutes,
)
from app.services.location_parse import normalize_campus_location

router = APIRouter(prefix="/api/commute", tags=["commute"])


@router.post("/estimate-batch", response_model=CommuteBatchResponse)
def estimate_commute_batch(
    payload: CommuteBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommuteBatchResponse:
    profile = get_profile_for_user(db, current_user)
    campus_query = normalize_campus_location(
        profile.campus_location or profile.university or ""
    )
    commute_mode = profile.commute_mode or "walking"

    if not campus_query:
        return CommuteBatchResponse(
            results={},
            campus_geocoded=False,
            commute_mode=commute_mode,
        )

    campus_coords = geocode(campus_query)
    if campus_coords is None:
        return CommuteBatchResponse(
            results={},
            campus_geocoded=False,
            commute_mode=commute_mode,
        )

    campus_lat, campus_lng = campus_coords
    geocoded_listings: list[tuple[int, float, float]] = []

    for item in payload.listings:
        address = item.address.strip()
        if len(address) < 3:
            continue

        listing_coords = geocode(address)
        if listing_coords is None:
            continue

        listing_lat, listing_lng = listing_coords
        geocoded_listings.append((item.id, listing_lat, listing_lng))

    routed = mapbox_batch_route_commutes(
        campus_lat, campus_lng, geocoded_listings, commute_mode
    )

    results: dict[int, CommuteEstimate] = {}
    for listing_id, listing_lat, listing_lng in geocoded_listings:
        if listing_id in routed:
            distance_miles, minutes = routed[listing_id]
        else:
            estimate = commute_between_coords(
                campus_lat,
                campus_lng,
                listing_lat,
                listing_lng,
                commute_mode,
            )
            if estimate is None:
                continue
            distance_miles, minutes = estimate

        results[listing_id] = CommuteEstimate(
            minutes=minutes,
            distance_miles=distance_miles,
        )

    return CommuteBatchResponse(
        results=results,
        campus_geocoded=True,
        commute_mode=commute_mode,
    )

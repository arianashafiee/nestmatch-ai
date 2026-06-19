from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


CommuteModeLiteral = Literal["walking", "transit", "biking", "driving"]
LivingSituationLiteral = Literal["solo", "roommates"]
AmenityTagLiteral = Literal[
    "laundry", "parking", "ac", "furnished", "no_basements"
]
ApartmentStatusLiteral = Literal[
    "pending",
    "interested",
    "contacted",
    "tour_scheduled",
    "applied",
    "archived",
]


class StudentProfileBase(BaseModel):
    university: str = ""
    campus_location: str = ""
    max_rent: float = Field(default=1500, gt=0)
    max_commute_minutes: int = Field(default=30, gt=0, le=180)
    commute_mode: CommuteModeLiteral = "walking"
    living_situation: LivingSituationLiteral = "solo"
    roommate_count: int = Field(default=0, ge=0, le=10)
    must_haves: list[AmenityTagLiteral] = []
    dealbreakers: list[AmenityTagLiteral] = []
    full_name: str = ""
    phone_number: str = ""
    preferred_lease_length: str = ""


class StudentProfileUpdate(StudentProfileBase):
    pass


class StudentProfileResponse(StudentProfileBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ScoreBreakdown(BaseModel):
    affordability: int = Field(ge=0, le=100)
    commute: int = Field(ge=0, le=100)
    amenities: int = Field(ge=0, le=100)
    safety_comfort: int = Field(ge=0, le=100)
    student_fit: int = Field(ge=0, le=100)


class ListingAnalysis(BaseModel):
    title: str
    rent_monthly: Optional[float] = None
    location: str = ""
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    amenities: list[str] = []
    hidden_fees: list[str] = []
    lease_length: Optional[str] = None
    red_flags: list[str] = []
    missing_info: list[str] = []
    estimated_commute_minutes: Optional[int] = None
    compatibility_score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    pros: list[str] = []
    cons: list[str] = []
    follow_up_questions: list[str] = Field(min_length=3, max_length=3)


class LandlordContact(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_url: Optional[str] = None


class ParseListingRequest(BaseModel):
    listing_text: str = Field(min_length=10)
    profile_id: int = 1
    apartment_id: Optional[int] = None


class ParseListingResponse(BaseModel):
    id: int
    profile_id: int
    raw_text: str
    source_url: Optional[str]
    status: ApartmentStatusLiteral
    title: Optional[str] = None
    compatibility_score: Optional[int] = None
    analysis: Optional[ListingAnalysis] = None
    photos: list[str] = []
    source_site: Optional[str] = None
    is_favorite: bool = False
    landlord_contact: Optional[LandlordContact] = None
    parsed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    parsed_with: Literal["openai", "mock"] = "mock"

    model_config = {"from_attributes": True}


class ApartmentDraftCreate(BaseModel):
    raw_text: str = Field(min_length=10)
    source_url: Optional[str] = None
    photos: list[str] = []
    source_site: Optional[str] = None
    fetch_photos: bool = True


class SearchListingsRequest(BaseModel):
    profile_id: int = 1


class SearchListingItem(BaseModel):
    title: str
    url: str
    source_site: str
    rent: Optional[float] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    snippet: str = ""
    photos: list[str] = []
    location: str = ""
    listing_address: str = ""
    distance_miles: Optional[float] = None
    commute_minutes: Optional[int] = None
    raw_text: str = ""


class SearchListingsResponse(BaseModel):
    results: list[SearchListingItem]
    sources_searched: list[str]
    errors: dict[str, str] = {}
    location: str = ""
    search_area: str = ""
    max_rent: float = 0
    campus_geocoded: bool = False
    max_commute_minutes: int = 30
    commute_mode: CommuteModeLiteral = "walking"
    ai_ranked: bool = False
    ai_discovered: bool = False


class CommuteListingInput(BaseModel):
    id: int
    address: str = Field(min_length=3, max_length=500)


class CommuteBatchRequest(BaseModel):
    listings: list[CommuteListingInput] = Field(max_length=100)


class CommuteEstimate(BaseModel):
    minutes: int
    distance_miles: float


class CommuteBatchResponse(BaseModel):
    results: dict[int, CommuteEstimate]
    campus_geocoded: bool = False
    commute_mode: CommuteModeLiteral = "walking"


class AppConfigResponse(BaseModel):
    ai_mode: Literal["openai", "mock"]
    mapbox_configured: bool
    mapbox_token: Optional[str] = None
    mapbox_style_url: str = "mapbox://styles/mapbox/streets-v12"
    database: str
    search_sources: list[str] = [
        "jhu_housing",
        "apartments.com",
        "rent.com",
        "zillow.com",
        "craigslist",
        "realtor.com",
    ]


class ApartmentResponse(BaseModel):
    id: int
    profile_id: int
    raw_text: str
    source_url: Optional[str]
    status: ApartmentStatusLiteral
    title: Optional[str] = None
    compatibility_score: Optional[int] = None
    analysis: Optional[ListingAnalysis] = None
    photos: list[str] = []
    source_site: Optional[str] = None
    is_favorite: bool = False
    landlord_contact: Optional[LandlordContact] = None
    tour_at: Optional[datetime] = None
    tour_notes: list[dict] = []
    parsed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    listing_address: str = ""

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def attach_listing_address(cls, data):
        from app.models import ApartmentListing
        from app.services.listing_address import extract_listing_address

        if isinstance(data, ApartmentListing):
            from app.services.image_quality import normalize_photo_list

            payload = {
                "id": data.id,
                "profile_id": data.profile_id,
                "raw_text": data.raw_text,
                "source_url": data.source_url,
                "status": data.status,
                "title": data.title,
                "compatibility_score": data.compatibility_score,
                "analysis": data.analysis,
                "photos": normalize_photo_list(
                    data.photos or [],
                    data.source_site or "",
                    limit=20,
                ),
                "source_site": data.source_site,
                "is_favorite": bool(getattr(data, "is_favorite", False)),
                "landlord_contact": data.landlord_contact,
                "tour_at": getattr(data, "tour_at", None),
                "tour_notes": getattr(data, "tour_notes", None) or [],
                "parsed_at": data.parsed_at,
                "created_at": data.created_at,
                "listing_address": extract_listing_address(data.raw_text or ""),
            }
            return payload
        if isinstance(data, dict) and not data.get("listing_address"):
            data = dict(data)
            data["listing_address"] = extract_listing_address(
                str(data.get("raw_text") or "")
            )
        return data


class ApartmentStatusUpdate(BaseModel):
    status: Optional[ApartmentStatusLiteral] = None
    is_favorite: Optional[bool] = None
    tour_at: Optional[datetime] = None
    tour_notes: Optional[list[dict]] = None


class TourNoteSchema(BaseModel):
    id: str
    text: str
    created_at: datetime

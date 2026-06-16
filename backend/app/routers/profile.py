from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import StudentProfile, User
from app.schemas import StudentProfileResponse, StudentProfileUpdate
from app.services.location_parse import normalize_campus_location

router = APIRouter(prefix="/api/profile", tags=["profile"])


def get_profile_for_user(db: Session, user: User) -> StudentProfile:
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=StudentProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProfile:
    try:
        profile = get_profile_for_user(db, current_user)
        normalized = normalize_campus_location(profile.campus_location or "")
        if normalized and normalized != (profile.campus_location or ""):
            profile.campus_location = normalized
            db.commit()
            db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check that the backend can write to its database file.",
        ) from exc


@router.put("", response_model=StudentProfileResponse)
def upsert_profile(
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentProfile:
    try:
        profile = get_profile_for_user(db, current_user)
        payload_data = payload.model_dump()
        if payload_data.get("campus_location"):
            payload_data["campus_location"] = normalize_campus_location(
                payload_data["campus_location"]
            )
        for field, value in payload_data.items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Could not save profile to the database.",
        ) from exc

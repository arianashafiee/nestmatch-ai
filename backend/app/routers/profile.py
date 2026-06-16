from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentProfile
from app.schemas import StudentProfileResponse, StudentProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])

DEFAULT_PROFILE_ID = 1


def get_or_create_profile(db: Session) -> StudentProfile:
    profile = db.get(StudentProfile, DEFAULT_PROFILE_ID)
    if profile is None:
        profile = StudentProfile(id=DEFAULT_PROFILE_ID)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=StudentProfileResponse)
def get_profile(db: Session = Depends(get_db)) -> StudentProfile:
    try:
        return get_or_create_profile(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check that the backend can write to its database file.",
        ) from exc


@router.put("", response_model=StudentProfileResponse)
def upsert_profile(
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
) -> StudentProfile:
    try:
        profile = get_or_create_profile(db)
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Could not save profile to the database. Your browser copy is still kept locally.",
        ) from exc

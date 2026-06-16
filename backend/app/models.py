from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    profile: Mapped[Optional["StudentProfile"]] = relationship(
        back_populates="user",
        uselist=False,
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=True
    )
    university: Mapped[str] = mapped_column(String(255), default="")
    campus_location: Mapped[str] = mapped_column(String(500), default="")
    max_rent: Mapped[float] = mapped_column(Float, default=1500.0)
    max_commute_minutes: Mapped[int] = mapped_column(Integer, default=30)
    commute_mode: Mapped[str] = mapped_column(String(20), default="walking")
    living_situation: Mapped[str] = mapped_column(String(20), default="solo")
    roommate_count: Mapped[int] = mapped_column(Integer, default=0)
    must_haves: Mapped[list] = mapped_column(JSON, default=list)
    dealbreakers: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[Optional[User]] = relationship(back_populates="profile")


class ApartmentListing(Base):
    __tablename__ = "apartment_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, default=1)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")

    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    compatibility_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    photos: Mapped[list] = mapped_column(JSON, default=list)
    source_site: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(default=False)
    landlord_contact: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── User schemas ───────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., pattern=r"^\+?2507[2-9]\d{7}$",
                       description="Rwanda phone: +2507XXXXXXXX")
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    phone: str
    password: str


class UserPublic(BaseModel):
    id: int
    full_name: str
    phone: str
    email: Optional[str]
    is_verified: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    average_rating: Optional[float]
    total_trips: int
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ── Ride schemas ───────────────────────────────────────────────────────────────

class RideCreate(BaseModel):
    origin_city: str = Field(..., min_length=2)
    destination_city: str = Field(..., min_length=2)
    origin_detail: Optional[str] = None
    destination_detail: Optional[str] = None
    departure_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    departure_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    total_seats: int = Field(..., ge=1, le=8)
    price_per_seat: int = Field(..., ge=500, description="Minimum 500 RWF")
    car_model: Optional[str] = None
    car_plate: Optional[str] = None
    tags: Optional[List[str]] = []

    @field_validator("tags")
    @classmethod
    def max_tags(cls, v):
        if v and len(v) > 6:
            raise ValueError("Maximum 6 tags allowed")
        return v


class RideResponse(BaseModel):
    id: int
    driver: UserPublic
    origin_city: str
    destination_city: str
    origin_detail: Optional[str]
    destination_detail: Optional[str]
    departure_date: str
    departure_time: str
    total_seats: int
    available_seats: int
    price_per_seat: int
    car_model: Optional[str]
    car_plate: Optional[str]
    tags: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_tags(cls, ride):
        data = {
            **{c.name: getattr(ride, c.name) for c in ride.__table__.columns},
            "driver": ride.driver,
            "tags": ride.tags_list,
        }
        return cls(**data)


class RideSearch(BaseModel):
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    departure_date: Optional[str] = None
    min_seats: int = Field(default=1, ge=1)


# ── Booking schemas ────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    ride_id: int
    seats_booked: int = Field(..., ge=1, le=8)


class BookingResponse(BaseModel):
    id: int
    ride: RideResponse
    passenger: UserPublic
    seats_booked: int
    total_price: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Payment schemas ────────────────────────────────────────────────────────────

class PaymentInitiate(BaseModel):
    booking_id: int
    provider: str = Field(..., pattern="^(mtn_momo|airtel)$")
    phone_number: str = Field(
        ..., pattern=r"^\+?2507[2-9]\d{7}$",
        description="Mobile money number (Rwanda)"
    )


class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    provider: str
    phone_number: str
    amount: int
    currency: str
    external_ref: Optional[str]
    status: str
    initiated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Rating schemas ─────────────────────────────────────────────────────────────

class RatingCreate(BaseModel):
    booking_id: int
    rated_user_id: int
    score: float = Field(..., ge=1.0, le=5.0)
    comment: Optional[str] = Field(None, max_length=500)

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from core.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class BookingStatus(str, enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(str, enum.Enum):
    PENDING    = "pending"
    SUCCESS    = "success"
    FAILED     = "failed"
    REFUNDED   = "refunded"


class PaymentProvider(str, enum.Enum):
    MTN_MOMO = "mtn_momo"
    AIRTEL   = "airtel"


# ── User ───────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String(120), nullable=False)
    phone         = Column(String(20), unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)   # phone/ID verification
    avatar_url    = Column(String(500), nullable=True)
    bio           = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rides_offered = relationship("Ride", back_populates="driver", foreign_keys="Ride.driver_id")
    bookings      = relationship("Booking", back_populates="passenger", foreign_keys="Booking.passenger_id")
    ratings_given = relationship("Rating", back_populates="rater", foreign_keys="Rating.rater_id")
    ratings_received = relationship("Rating", back_populates="rated_user", foreign_keys="Rating.rated_user_id")

    @property
    def average_rating(self):
        if not self.ratings_received:
            return None
        return round(sum(r.score for r in self.ratings_received) / len(self.ratings_received), 1)

    @property
    def total_trips(self):
        return len([b for b in self.bookings if b.status == BookingStatus.COMPLETED])


# ── Ride ───────────────────────────────────────────────────────────────────────

class Ride(Base):
    __tablename__ = "rides"

    id              = Column(Integer, primary_key=True, index=True)
    driver_id       = Column(Integer, ForeignKey("users.id"), nullable=False)

    origin_city     = Column(String(100), nullable=False, index=True)
    destination_city = Column(String(100), nullable=False, index=True)
    origin_detail   = Column(String(255), nullable=True)   # e.g. "Nyabugogo bus park"
    destination_detail = Column(String(255), nullable=True)

    departure_date  = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    departure_time  = Column(String(5), nullable=False)               # HH:MM

    total_seats     = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price_per_seat  = Column(Integer, nullable=False)   # in RWF

    car_model       = Column(String(100), nullable=True)
    car_plate       = Column(String(20), nullable=True)

    # Preferences / tags stored as comma-separated string
    tags            = Column(String(500), nullable=True)

    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships
    driver   = relationship("User", back_populates="rides_offered", foreign_keys=[driver_id])
    bookings = relationship("Booking", back_populates="ride")

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",")] if self.tags else []


# ── Booking ────────────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id           = Column(Integer, primary_key=True, index=True)
    ride_id      = Column(Integer, ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    seats_booked = Column(Integer, nullable=False, default=1)
    total_price  = Column(Integer, nullable=False)   # seats_booked × price_per_seat

    status       = Column(Enum(BookingStatus), default=BookingStatus.PENDING, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ride      = relationship("Ride", back_populates="bookings")
    passenger = relationship("User", back_populates="bookings", foreign_keys=[passenger_id])
    payment   = relationship("Payment", back_populates="booking", uselist=False)

    __table_args__ = (
        UniqueConstraint("ride_id", "passenger_id", name="uq_ride_passenger"),
    )


# ── Payment ────────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True, index=True)
    booking_id     = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True)

    provider       = Column(Enum(PaymentProvider), nullable=False)
    phone_number   = Column(String(20), nullable=False)   # payer's mobile money number
    amount         = Column(Integer, nullable=False)       # RWF
    currency       = Column(String(5), default="RWF")

    external_ref   = Column(String(255), nullable=True)   # MoMo / Airtel transaction ID
    provider_ref   = Column(String(255), nullable=True)   # our reference sent to provider

    status         = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    failure_reason = Column(Text, nullable=True)

    initiated_at   = Column(DateTime, default=datetime.utcnow)
    completed_at   = Column(DateTime, nullable=True)

    # Relationships
    booking = relationship("Booking", back_populates="payment")


# ── Rating ─────────────────────────────────────────────────────────────────────

class Rating(Base):
    __tablename__ = "ratings"

    id            = Column(Integer, primary_key=True, index=True)
    booking_id    = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    rater_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    rated_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score         = Column(Float, nullable=False)   # 1.0 – 5.0
    comment       = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    rater      = relationship("User", back_populates="ratings_given",    foreign_keys=[rater_id])
    rated_user = relationship("User", back_populates="ratings_received", foreign_keys=[rated_user_id])

    __table_args__ = (
        UniqueConstraint("booking_id", "rater_id", name="uq_booking_rater"),
    )

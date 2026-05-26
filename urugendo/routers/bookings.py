from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models import Booking, BookingStatus, Rating, Ride, User
from schemas import BookingCreate, RatingCreate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", status_code=201)
def create_booking(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Passenger books seats on a ride."""

    ride = db.query(Ride).filter(Ride.id == payload.ride_id, Ride.is_active == True).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found or no longer available")

    if ride.driver_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot book your own ride")

    if ride.available_seats < payload.seats_booked:
        raise HTTPException(
            status_code=409,
            detail=f"Only {ride.available_seats} seat(s) available"
        )

    # Check for duplicate booking
    existing = db.query(Booking).filter(
        Booking.ride_id == payload.ride_id,
        Booking.passenger_id == current_user.id,
        Booking.status != BookingStatus.CANCELLED,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a booking on this ride")

    total_price = ride.price_per_seat * payload.seats_booked

    booking = Booking(
        ride_id=payload.ride_id,
        passenger_id=current_user.id,
        seats_booked=payload.seats_booked,
        total_price=total_price,
        status=BookingStatus.PENDING,
    )
    ride.available_seats -= payload.seats_booked

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "id": booking.id,
        "ride_id": booking.ride_id,
        "passenger_id": booking.passenger_id,
        "seats_booked": booking.seats_booked,
        "total_price": booking.total_price,
        "status": booking.status,
        "created_at": booking.created_at,
        "message": "Booking created. Please proceed to payment to confirm your seat(s).",
    }


@router.get("/my")
def my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all bookings made by the current user (as a passenger)."""
    bookings = (
        db.query(Booking)
        .filter(Booking.passenger_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return [
        {
            "id": b.id,
            "ride": {
                "id": b.ride.id,
                "origin_city": b.ride.origin_city,
                "destination_city": b.ride.destination_city,
                "departure_date": b.ride.departure_date,
                "departure_time": b.ride.departure_time,
                "price_per_seat": b.ride.price_per_seat,
            },
            "seats_booked": b.seats_booked,
            "total_price": b.total_price,
            "status": b.status,
            "created_at": b.created_at,
        }
        for b in bookings
    ]


@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a specific booking (owner or driver only)."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.passenger_id != current_user.id and booking.ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return booking


@router.post("/{booking_id}/cancel", status_code=200)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Passenger cancels their booking."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.passenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status in (BookingStatus.CANCELLED, BookingStatus.COMPLETED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {booking.status} booking")

    booking.status = BookingStatus.CANCELLED
    booking.ride.available_seats += booking.seats_booked  # restore seats
    db.commit()

    return {"message": "Booking cancelled. Refund will be processed if payment was made."}


@router.post("/{booking_id}/confirm", status_code=200)
def confirm_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Driver confirms a passenger's booking."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the driver can confirm bookings")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Booking is already {booking.status}")

    booking.status = BookingStatus.CONFIRMED
    db.commit()
    return {"message": "Booking confirmed!"}


@router.post("/{booking_id}/rate")
def rate_user(
    booking_id: int,
    payload: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Leave a rating after a completed booking."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Can only rate completed bookings")

    # Ensure rater is part of this booking
    if current_user.id not in (booking.passenger_id, booking.ride.driver_id):
        raise HTTPException(status_code=403, detail="Not part of this booking")

    existing = db.query(Rating).filter(
        Rating.booking_id == booking_id,
        Rating.rater_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already rated this booking")

    rating = Rating(
        booking_id=booking_id,
        rater_id=current_user.id,
        rated_user_id=payload.rated_user_id,
        score=payload.score,
        comment=payload.comment,
    )
    db.add(rating)
    db.commit()
    return {"message": "Rating submitted. Thank you!"}

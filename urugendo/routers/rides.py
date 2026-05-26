from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models import Ride, User
from schemas import RideCreate, RideResponse

router = APIRouter(prefix="/rides", tags=["Rides"])


def _build_response(ride: Ride) -> dict:
    return {
        "id": ride.id,
        "driver": ride.driver,
        "origin_city": ride.origin_city,
        "destination_city": ride.destination_city,
        "origin_detail": ride.origin_detail,
        "destination_detail": ride.destination_detail,
        "departure_date": ride.departure_date,
        "departure_time": ride.departure_time,
        "total_seats": ride.total_seats,
        "available_seats": ride.available_seats,
        "price_per_seat": ride.price_per_seat,
        "car_model": ride.car_model,
        "car_plate": ride.car_plate,
        "tags": ride.tags_list,
        "is_active": ride.is_active,
        "created_at": ride.created_at,
    }


@router.post("/", status_code=201)
def create_ride(
    payload: RideCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Driver posts a new ride offer."""
    ride = Ride(
        driver_id=current_user.id,
        origin_city=payload.origin_city,
        destination_city=payload.destination_city,
        origin_detail=payload.origin_detail,
        destination_detail=payload.destination_detail,
        departure_date=payload.departure_date,
        departure_time=payload.departure_time,
        total_seats=payload.total_seats,
        available_seats=payload.total_seats,
        price_per_seat=payload.price_per_seat,
        car_model=payload.car_model,
        car_plate=payload.car_plate,
        tags=",".join(payload.tags) if payload.tags else None,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return _build_response(ride)


@router.get("/search")
def search_rides(
    origin: Optional[str] = Query(None, description="Origin city (partial match)"),
    destination: Optional[str] = Query(None, description="Destination city (partial match)"),
    date: Optional[str] = Query(None, description="Departure date YYYY-MM-DD"),
    min_seats: int = Query(1, ge=1, description="Minimum available seats"),
    max_price: Optional[int] = Query(None, description="Maximum price per seat in RWF"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Search available rides with filters."""
    q = db.query(Ride).filter(Ride.is_active == True, Ride.available_seats >= min_seats)

    if origin:
        q = q.filter(Ride.origin_city.ilike(f"%{origin}%"))
    if destination:
        q = q.filter(Ride.destination_city.ilike(f"%{destination}%"))
    if date:
        q = q.filter(Ride.departure_date == date)
    if max_price:
        q = q.filter(Ride.price_per_seat <= max_price)

    total = q.count()
    rides = q.order_by(Ride.departure_date, Ride.departure_time).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [_build_response(r) for r in rides],
    }


@router.get("/{ride_id}")
def get_ride(ride_id: int, db: Session = Depends(get_db)):
    """Get a single ride by ID."""
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    return _build_response(ride)


@router.get("/my/offered")
def my_offered_rides(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all rides the current user has offered as a driver."""
    rides = db.query(Ride).filter(Ride.driver_id == current_user.id).order_by(Ride.departure_date.desc()).all()
    return [_build_response(r) for r in rides]


@router.delete("/{ride_id}", status_code=204)
def cancel_ride(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Driver cancels (deactivates) their ride."""
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your ride")
    ride.is_active = False
    db.commit()

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models import Booking, BookingStatus, Payment, PaymentProvider, PaymentStatus, User
from schemas import PaymentInitiate, PaymentResponse
from services.payment_service import (
    airtel_check_payment_status,
    airtel_collect,
    mtn_check_payment_status,
    mtn_request_to_pay,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initiate", response_model=PaymentResponse, status_code=201)
async def initiate_payment(
    payload: PaymentInitiate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate a mobile money payment for a booking.
    Supports MTN MoMo and Airtel Money.
    """
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.passenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Booking is cancelled")

    # Prevent duplicate payment
    if booking.payment and booking.payment.status == PaymentStatus.SUCCESS:
        raise HTTPException(status_code=409, detail="Booking already paid")

    provider_enum = PaymentProvider(payload.provider)

    try:
        if provider_enum == PaymentProvider.MTN_MOMO:
            external_ref, status = await mtn_request_to_pay(
                phone=payload.phone_number,
                amount=booking.total_price,
                booking_id=booking.id,
            )
        else:  # airtel
            external_ref, status = await airtel_collect(
                phone=payload.phone_number,
                amount=booking.total_price,
                booking_id=booking.id,
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {str(e)}")

    payment = Payment(
        booking_id=booking.id,
        provider=provider_enum,
        phone_number=payload.phone_number,
        amount=booking.total_price,
        currency="RWF",
        external_ref=external_ref,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{payment_id}/status", response_model=PaymentResponse)
async def check_payment_status(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll the current status of a payment (for frontend polling)."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.booking.passenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if payment.status == PaymentStatus.PENDING and payment.external_ref:
        try:
            if payment.provider == PaymentProvider.MTN_MOMO:
                new_status = await mtn_check_payment_status(payment.external_ref)
            else:
                new_status = await airtel_check_payment_status(payment.external_ref)

            if new_status != "pending":
                payment.status = PaymentStatus(new_status)
                if new_status == "success":
                    payment.completed_at = datetime.utcnow()
                    payment.booking.status = BookingStatus.CONFIRMED
                db.commit()
                db.refresh(payment)
        except Exception:
            pass  # keep pending; will retry on next poll

    return payment


@router.post("/mtn/callback")
async def mtn_callback(request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint for MTN MoMo payment status updates.
    MTN calls this URL automatically after payment is processed.
    """
    body = await request.json()
    reference_id = request.headers.get("X-Reference-Id")
    if not reference_id:
        return {"status": "ignored"}

    payment = db.query(Payment).filter(Payment.external_ref == reference_id).first()
    if not payment:
        return {"status": "not_found"}

    mtn_status = body.get("status", "").upper()
    if mtn_status == "SUCCESSFUL":
        payment.status = PaymentStatus.SUCCESS
        payment.completed_at = datetime.utcnow()
        payment.booking.status = BookingStatus.CONFIRMED
    elif mtn_status == "FAILED":
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = body.get("reason", "Unknown")
        # Restore seats on failed payment
        payment.booking.ride.available_seats += payment.booking.seats_booked
        payment.booking.status = BookingStatus.CANCELLED

    db.commit()
    return {"status": "processed"}


@router.post("/airtel/callback")
async def airtel_callback(request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint for Airtel Money payment notifications.
    """
    body = await request.json()
    transaction_id = body.get("transaction", {}).get("id")
    if not transaction_id:
        return {"status": "ignored"}

    payment = db.query(Payment).filter(Payment.external_ref == transaction_id).first()
    if not payment:
        return {"status": "not_found"}

    airtel_status = body.get("transaction", {}).get("status", "").upper()
    if airtel_status == "TS":  # Transaction Successful
        payment.status = PaymentStatus.SUCCESS
        payment.completed_at = datetime.utcnow()
        payment.booking.status = BookingStatus.CONFIRMED
    elif airtel_status == "TF":  # Transaction Failed
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Airtel payment failed"
        payment.booking.ride.available_seats += payment.booking.seats_booked
        payment.booking.status = BookingStatus.CANCELLED

    db.commit()
    return {"status": "processed"}

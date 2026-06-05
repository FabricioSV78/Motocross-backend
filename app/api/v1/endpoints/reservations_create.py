from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.reservation_schema import (
    ReservationCreateRequest,
    PaymentIntentResponse,
    DirectConfirmReservationResponse,
)
from app.services.reservation_service import ReservationService


router = APIRouter()


# ============================================================================
# HU-19: POST /reservations - Create reservation + PaymentIntent
# ============================================================================

@router.post("/", response_model=Union[PaymentIntentResponse, DirectConfirmReservationResponse])
def create_reservation(
    request: ReservationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create reservation and get Stripe PaymentIntent.

    **HU-19: Checkout**

    **Important**: User must be authenticated as PILOT.

    Request Example:
    ```json
    {
      "trackId": 1,
      "date": "2026-05-20",
      "startTime": "09:00",
      "endTime": "12:00",
      "pilotType": "SENIOR",
      "coachId": 3,
      "classType": "HOURLY",
      "mode": "GROUP",
      "participants": 2
    }
    ```

    Response Example:
    ```json
    {
      "reservationId": 123,
      "stripePaymentIntentId": "pi_1234567890",
      "clientSecret": "pi_1234567890_secret_9876543210",
      "total": 462,
      "status": "PENDING_PAYMENT",
      "currency": "AUD",
      "demoMode": false
    }
    ```

    **Flow**:
    1. Validate track availability
    2. Validate coach availability (if applicable)
    3. Create Reservation with PENDING_PAYMENT
    4. Create Stripe PaymentIntent
    5. Return client_secret for Stripe Elements

    **Security**:
    - Only authenticated PILOTs can create reservations
    - Each reservation is linked to the creator user_id
    """
    role_value = getattr(current_user.role, "value", current_user.role)
    if role_value != "PILOT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pilot users can create reservations",
        )

    # If skip_payment is requested (default True), create reservation without PaymentIntent
    if getattr(request, "skip_payment", True):
        reservation_info = ReservationService.create_reservation_without_payment(
            db=db,
            user_id=current_user.id,
            track_id=request.track_id,
            reservation_date=request.date,
            start_time=request.start_time,
            end_time=request.end_time,
            pilot_type=request.pilot_type,
            class_type=request.class_type,
            mode=request.mode,
            coach_id=request.coach_id,
            track_reservation_type=request.track_reservation_type,
            participants=request.participants,
        )

        return DirectConfirmReservationResponse(
            reservation_id=reservation_info["reservation_id"],
            total=reservation_info["total"],
            status="CONFIRMED",
            currency=reservation_info["currency"],
            message="Reservation confirmed successfully",
        )

    # Otherwise, proceed with PaymentIntent creation
    payment_info = ReservationService.create_reservation(
        db=db,
        user_id=current_user.id,
        track_id=request.track_id,
        reservation_date=request.date,
        start_time=request.start_time,
        end_time=request.end_time,
        pilot_type=request.pilot_type,
        class_type=request.class_type,
        mode=request.mode,
        coach_id=request.coach_id,
        track_reservation_type=request.track_reservation_type,
        participants=request.participants,
    )

    return PaymentIntentResponse(
        reservation_id=payment_info["reservation_id"],
        stripe_payment_intent_id=payment_info["stripe_payment_intent_id"],
        client_secret=payment_info["client_secret"],
        total=payment_info["total"],
        status=payment_info["status"],
        currency=payment_info["currency"],
    )


# ============================================================================
# POST /reservations/direct-confirm - Create reservation without payment
# ============================================================================

@router.post("/direct-confirm", response_model=DirectConfirmReservationResponse)
def create_reservation_without_payment(
    request: ReservationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a reservation confirmed directly without payment.

    **Different from POST /reservations**:
    - No Stripe PaymentIntent
    - Reservation is created with CONFIRMED status
    - No further payment required

    Useful for:
    - Testing and development
    - Future direct payment integrations
    - Offers or courtesy bookings

    Response Example:
    ```json
    {
      "reservationId": 123,
      "total": 462,
      "status": "CONFIRMED",
      "currency": "AUD",
      "message": "Reserva confirmada exitosamente"
    }
    ```
    """
    role_value = getattr(current_user.role, "value", current_user.role)
    if role_value != "PILOT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pilot users can create reservations",
        )

    reservation_info = ReservationService.create_reservation_without_payment(
        db=db,
        user_id=current_user.id,
        track_id=request.track_id,
        reservation_date=request.date,
        start_time=request.start_time,
        end_time=request.end_time,
        pilot_type=request.pilot_type,
        class_type=request.class_type,
        mode=request.mode,
        coach_id=request.coach_id,
        track_reservation_type=request.track_reservation_type,
        participants=request.participants,
    )

    return DirectConfirmReservationResponse(
        reservation_id=reservation_info["reservation_id"],
        total=reservation_info["total"],
        status="CONFIRMED",
        currency=reservation_info["currency"],
        message="Reservation confirmed successfully",
    )

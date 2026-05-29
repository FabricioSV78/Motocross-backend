from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.reservation_schema import (
    ReservationCalculateRequest,
    ReservationCalculateResponse,
)
from app.services.reservation_service import ReservationService


router = APIRouter()


# ============================================================================
# HU-18: POST /reservations/calculate - Quote
# ============================================================================

@router.post("/calculate", response_model=ReservationCalculateResponse)
def calculate_reservation(
    request: ReservationCalculateRequest,
    db: Session = Depends(get_db),
):
    """
    Calculate reservation cost without creating the reservation.

    **HU-18: Quote**

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
      "trackPrice": 60,
      "coachPrice": 80,
      "totalDurationHours": 3,
      "subtotal": 420,
      "tax": 42,
      "total": 462,
      "currency": "AUD",
      "availabilityAvailable": true
    }
    ```
    """
    cost_info = ReservationService.calculate_reservation_cost(
        db=db,
        track_id=request.track_id,
        reservation_date=request.date,
        start_time=request.start_time,
        end_time=request.end_time,
        pilot_type=request.pilot_type,
        coach_id=request.coach_id,
      class_type=request.class_type,
      track_reservation_type=request.track_reservation_type,
        mode=request.mode,
        participants=request.participants,
    )

    return ReservationCalculateResponse(**cost_info)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.reservation_schema import (
    CancelReservationResponse,
    ReservationDetailResponse,
    ReservationListResponse,
)
from app.services.reservation_service import ReservationService


router = APIRouter()


def _reservation_list_response(res) -> ReservationListResponse:
    return ReservationListResponse(
        id=res.id,
        track_id=res.track_id,
        track_name=res.track.name if res.track else "Unknown",
        coach_id=res.coach_id,
        coach_name=res.coach.user.nombre if res.coach else None,
        pilot_name=res.user.nombre if res.user else None,
        reservation_date=res.reservation_date,
        start_time=res.start_time,
        end_time=res.end_time,
        participants=res.participants,
        pilot_type=getattr(res.pilot_type, "value", res.pilot_type),
        class_type=res.class_type,
        class_mode=res.class_mode,
        track_price=res.track_price,
        coach_price=res.coach_price,
        total_amount=res.total_amount,
        coach_earnings=res.coach_price,
        status=getattr(res.status, "value", res.status),
        created_at=res.created_at.isoformat(),
    )


# ============================================================================
# GET /reservations - List my reservations
# ============================================================================

@router.get("/", response_model=list[ReservationListResponse])
def list_my_reservations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all reservations for the authenticated user.

    **Returns**: List ordered by date (most recently created first)
    """
    reservations = ReservationService.get_user_reservations(db, current_user.id)

    return [_reservation_list_response(res) for res in reservations]


# ============================================================================
# GET /reservations/{id} - Reservation details
# ============================================================================

@router.get("/{reservation_id}", response_model=ReservationDetailResponse)
def get_reservation_detail(
    reservation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get full reservation details.

    **Security**: Only the owner can view the reservation.
    """
    reservation = ReservationService.get_reservation_detail(
        db, reservation_id, current_user.id
    )


    payment_detail = None
    if reservation.payment:
        payment_detail = {
            "id": reservation.payment.id,
            "stripe_payment_intent_id": reservation.payment.stripe_payment_intent_id,
            "amount": reservation.payment.amount,
            "currency": reservation.payment.currency,
            "status": reservation.payment.status,
            "created_at": reservation.payment.created_at.isoformat(),
        }

    return ReservationDetailResponse(
        id=reservation.id,
        track={
            "id": reservation.track.id,
            "name": reservation.track.name,
            "location": f"{reservation.track.latitude},{reservation.track.longitude}",
        },
        coach={
            "id": reservation.coach.id,
            "nombre": reservation.coach.user.nombre,
        } if reservation.coach else None,
        reservation_date=reservation.reservation_date,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        participants=reservation.participants,
        pilot_type=reservation.pilot_type,
        class_type=reservation.class_type,
        class_mode=reservation.class_mode,
        track_price=reservation.track_price,
        coach_price=reservation.coach_price,
        total_amount=reservation.total_amount,
        status=reservation.status,
        payment=payment_detail,
        created_at=reservation.created_at.isoformat(),
    )


@router.patch("/{reservation_id}/cancel", response_model=CancelReservationResponse)
def cancel_my_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Cancelar una reserva propia del piloto.

    El cambio se refleja en las vistas del piloto, coach y empresa porque todas
    leen el mismo estado de la reserva.
    """
    reservation = ReservationService.cancel_reservation(
        db=db,
        reservation_id=reservation_id,
        user_id=current_user.id,
    )
    return CancelReservationResponse(
        reservation_id=reservation.id,
        status=getattr(reservation.status, "value", reservation.status),
        message="Reservation cancelled successfully",
    )


# ============================================================================
# GET /reservations/coach/mine - Coach reservations
# ============================================================================

@router.get("/coach/mine", response_model=list[ReservationListResponse])
def get_coach_reservations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all reservations for the authenticated coach.

    **Security**: Only COACH users can access.
    """
    role_value = getattr(current_user.role, "value", current_user.role)
    if role_value != "COACH":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo COACHES pueden ver sus reservas",
        )

    from app.repositories.coach_repository import CoachRepository
    coach_repo = CoachRepository(db)
    coach = coach_repo.get_by_user_id(current_user.id)

    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de coach no encontrado",
        )

    reservations = ReservationService.get_coach_reservations(db, coach.id)

    return [_reservation_list_response(res) for res in reservations]


# ============================================================================
# GET /reservations/track/{track_id} - Track reservations
# ============================================================================

@router.get("/track/{track_id}", response_model=list[ReservationListResponse])
def get_track_reservations(
    track_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all reservations for a track.

    **Security**: Only the owning company can view the track reservations.
    """
    from app.repositories.tracks_repository import TracksRepository
    track_repo = TracksRepository(db)
    track = track_repo.get_by_id(track_id)

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pista no encontrada",
        )

    if track.company_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la empresa propietaria puede ver las reservas de la pista",
        )

    reservations = ReservationService.get_track_reservations(db, track_id)

    return [_reservation_list_response(res) for res in reservations]

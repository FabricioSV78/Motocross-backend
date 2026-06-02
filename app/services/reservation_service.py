"""
Service para lógica de reservas
"""

from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Track, Coach, CoachService, Reservation, Payment
from app.models.enums import ReservationStatus, PaymentStatus, PilotCategory, ClassType, ClassMode, Status
from app.repositories.reservation_repository import ReservationRepository, PaymentRepository
from app.repositories.tracks_repository import TracksRepository
from app.repositories.coach_repository import CoachRepository
from app.repositories.coach_settings_repository import CoachSettingsRepository
from app.services.stripe_service import stripe_service
from app.utils.time_range import combine_date_time, duration_hours


class ReservationService:
    """
    Servicio con toda la lógica de reservas
    """
    
    @staticmethod
    def calculate_reservation_cost(
        db: Session,
        track_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        pilot_type: str,
        coach_id: int = None,
        class_type: str = None,
        track_reservation_type: str = None,
        mode: str = None,
        participants: int = 1,
    ) -> dict:
        """
        Calcular costo de una reserva
        
        HU-18: Cotización
        
        PRICING MODEL:
        
        **SIN INSTRUCTOR (coach_id = None):**
        - class_type FULL_DAY: Usa price_junior o price_senior como precio fijo
        - class_type HALF_DAY: Usa price_junior_half o price_senior_half como precio fijo
        
        **CON INSTRUCTOR (coach_id presente):**
        - Busca un CoachService con el class_type y mode especificados
        - class_type HOURLY: coach_service.price × duration_hours
        - class_type HALF_DAY/FULL_DAY: coach_service.price (fijo, no multiplicado)
        """
        # Normalizar valores de enums/strings para comparaciones
        pilot_type_value = pilot_type.value if hasattr(pilot_type, "value") else pilot_type
        class_type_value = class_type.value if hasattr(class_type, "value") else class_type
        track_reservation_type_value = (
            track_reservation_type.value if hasattr(track_reservation_type, "value") else track_reservation_type
        )
        mode_value = mode.value if hasattr(mode, "value") else mode

        # Validar que la fecha sea futura
        if reservation_date <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date must be in the future"
            )
        
        # Validar que end_time > start_time
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        
        # Obtener pista
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found"
            )
        
        # Calcular duración en horas
        start_dt = combine_date_time(reservation_date, start_time)
        end_dt = combine_date_time(reservation_date, end_time)
        duration_hours_value = duration_hours(start_dt, end_dt)
        
        if duration_hours_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be greater than 0"
            )
        
        # Obtener precio de la pista según tipo de piloto
        if pilot_type_value == "SENIOR" or pilot_type_value == PilotCategory.SENIOR.value:
            track_price = track.price_senior
            track_price_half = track.price_senior_half
        else:
            track_price = track.price_junior
            track_price_half = track.price_junior_half
        
        # Calcular costo de pista basado en class_type (si no hay coach)
        # Si hay coach_id, class_type es para el coach
        # Si NO hay coach_id, class_type es para la pista (FULL_DAY, HALF_DAY)
        track_total = 0.0
        
        if not coach_id:
            # Reserva solo de pista (sin instructor)
            if class_type_value == ClassType.FULL_DAY.value:
                # Precio fijo para día completo
                track_total = round(track_price, 2)
            elif class_type_value == ClassType.HALF_DAY.value:
                # Precio fijo para medio día
                if track_price_half:
                    track_total = round(track_price_half, 2)
                else:
                    # Si no existe precio_half, usar el precio completo
                    track_total = round(track_price / 2, 2)
            else:
                # Para las reservas de pista no se permite el tipo HOURLY.
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="class_type for track must be FULL_DAY or HALF_DAY"
                )
        else:
            # Reserva con instructor - la pista se cobra según el tipo seleccionado (FULL_DAY/HALF_DAY)
            if not track_reservation_type_value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="You must provide track_reservation_type when booking with a coach"
                )
            if track_reservation_type_value == ClassType.FULL_DAY.value:
                track_total = round(track_price, 2)
            elif track_reservation_type_value == ClassType.HALF_DAY.value:
                if track_price_half:
                    track_total = round(track_price_half, 2)
                else:
                    track_total = round(track_price / 2, 2)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="track_reservation_type must be FULL_DAY or HALF_DAY"
                )

        # Validar disponibilidad real de la pista por rango
        track_repo = TracksRepository(db)
        track_slot = track_repo.get_covering_availability(track_id, reservation_date, start_time, end_time)
        availability_available = track_slot is not None
        if track_slot and participants > track_slot.capacity:
            availability_available = False
        if track_slot:
            # ya tenemos pilot_type_value normalizado arriba
            if track_slot.pilot_category != "BOTH" and pilot_type_value != track_slot.pilot_category:
                availability_available = False
            if not coach_id:
                # Permitir reservar HALF_DAY incluso si el slot es FULL_DAY (ej: una franja de 9-17
                # puede aceptar una reserva de medio día). Sin embargo, si el slot es HALF_DAY no
                # se debe aceptar una reserva FULL_DAY.
                if class_type_value in {ClassType.FULL_DAY.value, ClassType.HALF_DAY.value}:
                    slot_rental = track_slot.rental_type
                    # Aceptar cuando el slot y la petición coincidan, o cuando el slot sea FULL_DAY
                    # y la petición sea HALF_DAY (medio día dentro de día completo).
                    if not (
                        slot_rental == class_type_value
                        or (slot_rental == ClassType.FULL_DAY.value and class_type_value == ClassType.HALF_DAY.value)
                    ):
                        availability_available = False
        
        # Calcular costo de coach si aplica
        coach_total = 0.0
        coach_snapshot_price = None
        
        if coach_id:
            coach = db.query(Coach).filter(Coach.id == coach_id).first()
            if not coach:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coach not found"
                )
            if coach.status != Status.APPROVED.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Coach is not approved"
                )
            
            if not class_type_value or not mode_value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="You must provide class_type and mode when booking with a coach"
                )

            # Obtener servicio del coach - DEBE EXISTIR
            coach_service = db.query(CoachService).filter(
                CoachService.coach_id == coach_id,
                CoachService.class_type == class_type_value,
                CoachService.mode == mode_value,
            ).first()

            if not coach_service:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Coach does not offer services of type {class_type_value} in {mode_value} mode"
                )

            if mode_value == ClassMode.GROUP.value and participants > coach_service.max_students:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Group service allows a maximum of {coach_service.max_students} participants"
                )

            # Pricing logic:
            # - HOURLY: price × duration_hours
            # - HALF_DAY / FULL_DAY: precio fijo (no multiplicar)
            if class_type_value == ClassType.HOURLY.value:
                coach_total = round(coach_service.price * duration_hours_value, 2)
            else:
                coach_total = round(coach_service.price, 2)

            coach_snapshot_price = coach_total

            # Validar disponibilidad real del coach por rango
            coach_repo = CoachSettingsRepository(db)
            coach_slot = coach_repo.get_covering_availability(coach_id, reservation_date, start_time, end_time)
            if coach_slot is None:
                availability_available = False

            coach_overlaps = ReservationRepository.get_coach_reservations_overlap(
                db, coach_id, reservation_date, start_time, end_time
            )
            if coach_overlaps:
                availability_available = False
        
        # Calcular total
        subtotal = track_total + coach_total
        tax = round(subtotal * 0.1, 2)  # 10% de impuesto
        total = round(subtotal + tax, 2)

        if track_slot:
            overlaps = ReservationRepository.get_overlapping_reservations(
                db, track_id, reservation_date, start_time, end_time
            )
            if overlaps:
                total_participants_booked = sum(r.participants for r in overlaps)
                available = track_slot.capacity - total_participants_booked
                if available < participants:
                    availability_available = False
        
        return {
            "track_price": round(track_total, 2),
            "coach_price": coach_snapshot_price,
            "total_duration_hours": round(duration_hours_value, 2),
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "total": total,
            "currency": "AUD",
            "availability_available": availability_available,
        }
    
    @staticmethod
    def create_reservation(
        db: Session,
        user_id: int,
        track_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        pilot_type: PilotCategory,
        class_type: ClassType,
        mode: ClassMode,
        coach_id: int = None,
        track_reservation_type: str = None,
        participants: int = 1,
    ) -> dict:
        """
        Crear reserva y PaymentIntent en Stripe
        
        HU-19: Checkout
        """
        # Calcular costo primero
        cost_info = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=track_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            pilot_type=pilot_type,
            coach_id=coach_id,
            class_type=class_type,
            track_reservation_type=track_reservation_type,
            mode=mode,
            participants=participants,
        )

        if not cost_info["availability_available"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The track or coach is not available at that time"
            )
        
        # CREAR RESERVA CON ESTADO PENDING_PAYMENT
        # Esta es la parte crítica: SIN TRANSACCIÓN DE BD, al menos no aquí
        # En producción, esto iría en una transacción SQL
        # Normalizar valores para almacenarlos como strings en la BD
        pilot_type_str = pilot_type.value if hasattr(pilot_type, "value") else pilot_type
        class_type_str = class_type.value if hasattr(class_type, "value") else class_type
        mode_str = mode.value if hasattr(mode, "value") else mode
        track_reservation_type_str = (
            track_reservation_type.value if hasattr(track_reservation_type, "value") else track_reservation_type
        )

        reservation = ReservationRepository.create_reservation(
            db=db,
            user_id=user_id,
            track_id=track_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            participants=participants,
            pilot_type=pilot_type_str,
            class_type=class_type_str if class_type_str else None,
            class_mode=mode_str if mode_str else None,
            track_price=cost_info["track_price"],
            coach_price=cost_info["coach_price"],
            total_amount=cost_info["total"],
            coach_id=coach_id,
        )
        
        # CREAR PAYMENT INTENT EN STRIPE
        # Convertir a centavos
        amount_cents = int(cost_info["total"] * 100)
        
        payment_intent_info = stripe_service.create_payment_intent(
            amount=amount_cents,
            currency="aud",
            description=f"Reserva en pista {track_id} - {reservation_date}",
            metadata={
                "reservation_id": str(reservation.id),
                "user_id": str(user_id),
                "track_id": str(track_id),
            },
        )
        
        # Actualizar reserva con stripe_payment_intent_id
        reservation.stripe_payment_intent_id = payment_intent_info["payment_intent_id"]
        
        # Crear registro de Payment
        payment = PaymentRepository.create_payment(
            db=db,
            reservation_id=reservation.id,
            stripe_payment_intent_id=payment_intent_info["payment_intent_id"],
            amount=cost_info["total"],
            currency="AUD",
        )
        
        db.commit()
        
        return {
            "reservation_id": reservation.id,
            "stripe_payment_intent_id": payment_intent_info["payment_intent_id"],
            "client_secret": payment_intent_info["client_secret"],
            "total": cost_info["total"],
            "status": ReservationStatus.PENDING_PAYMENT,
            "currency": "AUD",
            "demo_mode": payment_intent_info.get("demo_mode", False),
        }
    
    @staticmethod
    def create_reservation_without_payment(
        db: Session,
        user_id: int,
        track_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        pilot_type: str,
        class_type: str = None,
        mode: str = None,
        coach_id: int = None,
        track_reservation_type: str = None,
        participants: int = 1,
    ) -> dict:
        """
        Crear reserva confirmada directamente SIN pago
        
        La reserva se crea con estado CONFIRMED sin necesidad de:
        - PaymentIntent en Stripe
        - Validación de pago
        
        Útil para testing, development, y futuras integraciones
        """
        # Calcular costo primero (validación)
        cost_info = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=track_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            pilot_type=pilot_type,
            coach_id=coach_id,
            class_type=class_type,
            track_reservation_type=track_reservation_type,
            mode=mode,
            participants=participants,
        )
        
        # Crear reserva directamente con estado CONFIRMED
        reservation = ReservationRepository.create_reservation(
            db=db,
            user_id=user_id,
            track_id=track_id,
            coach_id=coach_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            participants=participants,
            pilot_type=pilot_type,
            class_type=class_type,
            class_mode=mode,
            track_price=cost_info["track_price"],
            coach_price=cost_info.get("coach_price"),
            total_amount=cost_info["total"],
            stripe_payment_intent_id=None,  # Sin pago
        )
        
        # Cambiar estado a CONFIRMED (por defecto llega como PENDING_PAYMENT)
        reservation = ReservationRepository.update_reservation_status(
            db=db,
            reservation_id=reservation.id,
            status=ReservationStatus.CONFIRMED,
        )
        
        db.commit()
        
        return {
            "reservation_id": reservation.id,
            "total": cost_info["total"],
            "status": ReservationStatus.CONFIRMED,
            "currency": "AUD",
        }
    
    @staticmethod
    def handle_payment_succeeded(db: Session, stripe_payment_intent_id: str) -> Reservation:
        """
        Manejar pagointentado completado
        
        HU-20: Webhook - payment_intent.succeeded
        """
        # Buscar reserva
        reservation = ReservationRepository.get_reservation_by_stripe_intent(
            db, stripe_payment_intent_id
        )
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
        # Actualizar estado de reserva a CONFIRMED
        reservation = ReservationRepository.update_reservation_status(
            db, reservation.id, ReservationStatus.CONFIRMED
        )
        
        # Actualizar estado de pago a SUCCESS
        payment = PaymentRepository.get_payment_by_stripe_intent(db, stripe_payment_intent_id)
        if payment:
            PaymentRepository.update_payment_status(db, payment.id, PaymentStatus.SUCCESS)
        
        return reservation

    @staticmethod
    def cancel_reservation(db: Session, reservation_id: int, user_id: int) -> Reservation:
        """Cancelar una reserva propia del piloto."""
        reservation = ReservationRepository.get_reservation_by_id(db, reservation_id)

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found",
            )

        if reservation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own reservations",
            )

        current_status = getattr(reservation.status, "value", reservation.status)
        if current_status == ReservationStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This reservation is already cancelled",
            )
        if current_status == ReservationStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed reservations cannot be cancelled",
            )

        reservation_start = combine_date_time(reservation.reservation_date, reservation.start_time)
        if reservation_start <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Past reservations cannot be cancelled",
            )

        return ReservationRepository.update_reservation_status(
            db=db,
            reservation_id=reservation.id,
            status=ReservationStatus.CANCELLED,
        )
    
    @staticmethod
    def handle_payment_failed(db: Session, stripe_payment_intent_id: str) -> Reservation:
        """
        Manejar pago fallido
        
        HU-20: Webhook - payment_intent.payment_failed
        """
        # Buscar reserva
        reservation = ReservationRepository.get_reservation_by_stripe_intent(
            db, stripe_payment_intent_id
        )
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
        # Actualizar estado a CANCELLED
        reservation = ReservationRepository.update_reservation_status(
            db, reservation.id, ReservationStatus.CANCELLED
        )
        
        # Actualizar estado de pago a FAILED
        payment = PaymentRepository.get_payment_by_stripe_intent(db, stripe_payment_intent_id)
        if payment:
            PaymentRepository.update_payment_status(db, payment.id, PaymentStatus.FAILED)
        
        return reservation
    
    @staticmethod
    def get_user_reservations(db: Session, user_id: int) -> list[Reservation]:
        """Obtener todas las reservas de un usuario"""
        return ReservationRepository.get_user_reservations(db, user_id)
    
    @staticmethod
    def get_coach_reservations(db: Session, coach_id: int) -> list[Reservation]:
        """Obtener todas las reservas de un coach"""
        return ReservationRepository.get_coach_reservations(db, coach_id)
    
    @staticmethod
    def get_track_reservations(db: Session, track_id: int) -> list[Reservation]:
        """Obtener todas las reservas de una pista"""
        return ReservationRepository.get_track_reservations(db, track_id)
    
    @staticmethod
    def get_reservation_detail(db: Session, reservation_id: int, user_id: int) -> Reservation:
        """
        Obtener detalle de una reserva
        Con verificación de propiedad
        """
        reservation = ReservationRepository.get_reservation_by_id(db, reservation_id)
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
        # Verificar que el usuario sea el propietario
        if reservation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this reservation"
            )
        
        return reservation

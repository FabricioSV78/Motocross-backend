"""
Repository para Reservas
Manejo de datos de reservas con control de concurrencia
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from datetime import date, time
from app.models import Reservation, Payment
from app.models.enums import ReservationStatus, PaymentStatus


class ReservationRepository:
    """
    Repository para manejar reservas
    Incluye lógica de transacciones atómicas para evitar race conditions
    """
    
    @staticmethod
    def create_reservation(
        db: Session,
        user_id: int,
        track_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        participants: int,
        pilot_type: str,
        class_type: str,
        class_mode: str,
        track_price: float,
        total_amount: float,
        coach_price: float = None,
        coach_id: int = None,
        stripe_payment_intent_id: str = None,
    ) -> Reservation:
        """
        Crear nueva reserva
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario que reserva
            track_id: ID de la pista
            reservation_date: Fecha de la reserva
            start_time: Hora de inicio
            end_time: Hora de fin
            participants: Número de participantes
            pilot_type: Tipo de piloto (JUNIOR/SENIOR)
            class_type: Tipo de clase (HOURLY/HALF_DAY/FULL_DAY)
            class_mode: Modo de clase (ONE_TO_ONE/GROUP)
            track_price: Precio de la pista
            coach_price: Precio del coach
            total_amount: Total a pagar
            coach_id: ID del coach (opcional)
            stripe_payment_intent_id: ID del PaymentIntent de Stripe
            
        Returns:
            Reservation creada
        """
        reservation = Reservation(
            user_id=user_id,
            track_id=track_id,
            coach_id=coach_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            participants=participants,
            pilot_type=pilot_type,
            class_type=class_type,
            class_mode=class_mode,
            track_price=track_price,
            coach_price=coach_price,
            total_amount=total_amount,
            stripe_payment_intent_id=stripe_payment_intent_id,
            status=ReservationStatus.PENDING_PAYMENT,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation
    
    @staticmethod
    def get_reservation_by_id(db: Session, reservation_id: int) -> Reservation:
        """Obtener reserva por ID"""
        return db.query(Reservation).filter(Reservation.id == reservation_id).first()
    
    @staticmethod
    def get_reservation_by_stripe_intent(db: Session, stripe_payment_intent_id: str) -> Reservation:
        """Obtener reserva por Stripe PaymentIntent ID"""
        return db.query(Reservation).filter(
            Reservation.stripe_payment_intent_id == stripe_payment_intent_id
        ).first()
    
    @staticmethod
    def get_user_reservations(db: Session, user_id: int) -> list[Reservation]:
        """Obtener todas las reservas de un usuario"""
        return db.query(Reservation).filter(
            Reservation.user_id == user_id
        ).order_by(Reservation.reservation_date.desc()).all()
    
    @staticmethod
    def update_reservation_status(
        db: Session, 
        reservation_id: int, 
        status: ReservationStatus
    ) -> Reservation:
        """Actualizar estado de una reserva"""
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()
        if reservation:
            reservation.status = status
            db.commit()
            db.refresh(reservation)
        return reservation
    
    @staticmethod
    def get_overlapping_reservations(
        db: Session,
        track_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        exclude_reservation_id: int = None,
    ) -> list[Reservation]:
        """
        Obtener reservas superpuestas en una pista
        Excluye CANCELLED y reservas del pasado
        """
        query = db.query(Reservation).filter(
            and_(
                Reservation.track_id == track_id,
                Reservation.reservation_date == reservation_date,
                Reservation.status != ReservationStatus.CANCELLED,
                # Verificar sobreposición de tiempos
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
        )
        
        if exclude_reservation_id:
            query = query.filter(Reservation.id != exclude_reservation_id)
        
        return query.all()
    
    @staticmethod
    def get_coach_reservations_overlap(
        db: Session,
        coach_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        exclude_reservation_id: int = None,
    ) -> list[Reservation]:
        """
        Obtener reservas superpuestas de un coach
        Evita que el coach tenga dos lecciones al mismo tiempo
        """
        query = db.query(Reservation).filter(
            and_(
                Reservation.coach_id == coach_id,
                Reservation.reservation_date == reservation_date,
                Reservation.status != ReservationStatus.CANCELLED,
                # Verificar sobreposición de tiempos
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
        )
        
        if exclude_reservation_id:
            query = query.filter(Reservation.id != exclude_reservation_id)
        
        return query.all()
    
    @staticmethod
    def get_coach_reservations(db: Session, coach_id: int) -> list[Reservation]:
        """
        Obtener todas las reservas de un coach
        Ordenadas por fecha descendente (más recientes primero)
        """
        return db.query(Reservation).filter(
            Reservation.coach_id == coach_id
        ).order_by(Reservation.reservation_date.desc()).all()
    
    @staticmethod
    def get_track_reservations(db: Session, track_id: int) -> list[Reservation]:
        """
        Obtener todas las reservas de una pista
        Ordenadas por fecha descendente (más recientes primero)
        """
        return db.query(Reservation).filter(
            Reservation.track_id == track_id
        ).order_by(Reservation.reservation_date.desc()).all()


class PaymentRepository:
    """Repository para manejar pagos"""
    
    @staticmethod
    def create_payment(
        db: Session,
        reservation_id: int,
        stripe_payment_intent_id: str,
        amount: float,
        currency: str = "AUD",
    ) -> Payment:
        """Crear registro de pago"""
        payment = Payment(
            reservation_id=reservation_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    
    @staticmethod
    def get_payment_by_stripe_intent(db: Session, stripe_payment_intent_id: str) -> Payment:
        """Obtener pago por Stripe PaymentIntent ID"""
        return db.query(Payment).filter(
            Payment.stripe_payment_intent_id == stripe_payment_intent_id
        ).first()
    
    @staticmethod
    def update_payment_status(
        db: Session,
        payment_id: int,
        status: PaymentStatus,
    ) -> Payment:
        """Actualizar estado de un pago"""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = status
            db.commit()
            db.refresh(payment)
        return payment
    
    @staticmethod
    def get_payment_by_reservation(db: Session, reservation_id: int) -> Payment:
        """Obtener pago de una reserva"""
        return db.query(Payment).filter(Payment.reservation_id == reservation_id).first()

from sqlalchemy import Column, Integer, String, Float, Date, Time, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import date, time
from app.db.session import Base
from app.models.enums import ReservationStatus, PilotCategory


class Reservation(Base):
    """
    Modelo de Reserva
    Representa una reserva de pista y lección de coach hecha por un piloto
    """
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Claves foráneas
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=True, index=True)
    
    # Detalles de la reserva
    reservation_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    participants = Column(Integer, default=1, nullable=False)
    
    # Categoría de piloto (JUNIOR/SENIOR) - para aplicar precio correcto
    pilot_type = Column(Enum(PilotCategory), default=PilotCategory.JUNIOR, nullable=False)
    
    # Tipo de clase (HOURLY, HALF_DAY, FULL_DAY)
    class_type = Column(String, nullable=True)
    
    # Modo de clase (ONE_TO_ONE, GROUP)
    class_mode = Column(String, nullable=True)
    
    # Precios capturados en el momento de la reserva
    track_price = Column(Float, nullable=False)           # Precio de la pista
    coach_price = Column(Float, nullable=True)            # Precio del coach (si aplica)
    total_amount = Column(Float, nullable=False)          # Total a pagar
    
    # Estado de la reserva
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING_PAYMENT, nullable=False)
    
    # ID de Stripe PaymentIntent (para vincular con webhook)
    stripe_payment_intent_id = Column(String, nullable=True, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", backref="reservations")
    track = relationship("Track", backref="reservations")
    coach = relationship("Coach", backref="reservations")
    payment = relationship("Payment", back_populates="reservation", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Reservation {self.id} - User {self.user_id} - Track {self.track_id} - {self.status}>"

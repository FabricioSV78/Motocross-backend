from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import PaymentStatus


class Payment(Base):
    """
    Modelo de Pago
    Registra transacciones de pago asociadas a reservas
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Clave foránea a reserva
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False, unique=True, index=True)
    
    # ID de Stripe PaymentIntent
    stripe_payment_intent_id = Column(String, nullable=False, unique=True, index=True)
    
    # Datos de la transacción
    amount = Column(Float, nullable=False)
    currency = Column(String, default="AUD", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación
    reservation = relationship("Reservation", back_populates="payment")
    
    def __repr__(self):
        return f"<Payment {self.id} - Reservation {self.reservation_id} - {self.status}>"

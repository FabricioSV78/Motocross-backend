"""
Schemas para Reservas y Pagos
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import date as DateType, time as TimeType
from typing import Optional


# ============================================================================
# HU-18: COTIZACIÓN (Calculate)
# ============================================================================

class ReservationCalculateRequest(BaseModel):
    """Request para calcular cotización"""
    track_id: int
    date: DateType = Field(..., description="Fecha de la reserva")
    start_time: TimeType = Field(..., description="Hora de inicio (HH:MM)")
    end_time: TimeType = Field(..., description="Hora de fin (HH:MM)")
    pilot_type: str = Field(default="JUNIOR", description="JUNIOR o SENIOR")
    coach_id: Optional[int] = Field(default=None, description="ID del coach (opcional)")
    class_type: Optional[str] = Field(default=None, description="Para pista: HALF_DAY o FULL_DAY. Para reserva con coach: HOURLY, HALF_DAY o FULL_DAY.")
    track_reservation_type: Optional[str] = Field(default=None, description="Tipo de reserva de la pista: HALF_DAY o FULL_DAY. Requerido si se reserva con coach.")
    mode: Optional[str] = Field(default=None, description="ONE_TO_ONE o GROUP (requerido si coach_id está presente)")
    participants: int = Field(default=1, ge=1)


class ReservationCalculateResponse(BaseModel):
    """Response de cotización"""
    track_price: float = Field(..., description="Importe total de la pista para el rango solicitado")
    coach_price: Optional[float] = Field(default=None, description="Importe total del coach para el rango solicitado")
    total_duration_hours: float = Field(..., description="Duración en horas")
    subtotal: float = Field(..., description="Subtotal sin impuestos")
    tax: float = Field(default=0, description="Impuestos")
    total: float = Field(..., description="Total a pagar")
    currency: str = Field(default="AUD")
    availability_available: bool = Field(default=True, description="¿Hay disponibilidad?")


# ============================================================================
# HU-19: CHECKOUT (Create Reservation)
# ============================================================================

class ReservationCreateRequest(BaseModel):
    """Request para crear reserva"""
    track_id: int
    date: DateType
    start_time: TimeType
    end_time: TimeType
    pilot_type: str = Field(default="JUNIOR")
    coach_id: Optional[int] = None
    class_type: Optional[str] = Field(default=None, description="Para pista: HALF_DAY o FULL_DAY. Para reserva con coach: HOURLY, HALF_DAY o FULL_DAY.")
    track_reservation_type: Optional[str] = Field(default=None, description="Tipo de reserva de la pista: HALF_DAY o FULL_DAY. Requerido si se reserva con coach.")
    mode: Optional[str] = Field(default=None, description="ONE_TO_ONE o GROUP. Requerido si la reserva incluye coach.")
    participants: int = Field(default=1, ge=1)
    skip_payment: bool = Field(default=True, description="Si es true, crea la reserva sin generar PaymentIntent (pago en persona)")


class PaymentIntentResponse(BaseModel):
    """Respuesta con PaymentIntent de Stripe"""
    reservation_id: int = Field(..., description="ID de la reserva creada")
    stripe_payment_intent_id: str = Field(..., description="ID del PaymentIntent en Stripe")
    client_secret: str = Field(..., description="Client secret para Stripe Elements")
    total: float = Field(..., description="Total a pagar")
    status: str = Field(default="PENDING_PAYMENT", description="Estado de la reserva")
    currency: str = Field(default="AUD")


class DirectConfirmReservationResponse(BaseModel):
    """Respuesta de reserva confirmada directamente (sin pago)"""
    reservation_id: int = Field(..., description="ID de la reserva creada")
    total: float = Field(..., description="Total de la reserva")
    status: str = Field(default="CONFIRMED", description="Estado de la reserva (siempre CONFIRMED)")
    currency: str = Field(default="AUD")
    message: str = Field(default="Reservation confirmed successfully")


class CancelReservationResponse(BaseModel):
    """Respuesta al cancelar una reserva"""
    reservation_id: int
    status: str = Field(default="CANCELLED")
    message: str = Field(default="Reservation cancelled successfully")


# ============================================================================
# HU-20: WEBHOOK STRIPE
# ============================================================================

class StripeWebhookEvent(BaseModel):
    """Evento de webhook de Stripe"""
    id: str
    type: str
    data: dict


# ============================================================================
# OBTENER RESERVAS
# ============================================================================

class CoachForReservation(BaseModel):
    """Coach en respuesta de reserva"""
    id: int
    nombre: str
    
    model_config = ConfigDict(from_attributes=True)


class TrackForReservation(BaseModel):
    """Track en respuesta de reserva"""
    id: int
    name: str
    location: str
    
    model_config = ConfigDict(from_attributes=True)


class PaymentDetailResponse(BaseModel):
    """Detalle de pago"""
    id: int
    stripe_payment_intent_id: str
    amount: float
    currency: str
    status: str
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class ReservationDetailResponse(BaseModel):
    """Respuesta detallada de una reserva"""
    id: int
    track: TrackForReservation
    coach: Optional[CoachForReservation] = None
    reservation_date: DateType
    start_time: TimeType
    end_time: TimeType
    participants: int
    pilot_type: str
    class_type: Optional[str]
    class_mode: Optional[str]
    track_price: float
    coach_price: Optional[float]
    total_amount: float
    status: str
    payment: Optional[PaymentDetailResponse] = None
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class ReservationListResponse(BaseModel):
    """Respuesta de lista de reservas"""
    id: int
    track_id: int
    track_name: str
    coach_id: Optional[int] = None
    coach_name: Optional[str] = None
    pilot_name: Optional[str] = None
    reservation_date: DateType
    start_time: TimeType
    end_time: TimeType
    participants: int = 1
    pilot_type: Optional[str] = None
    class_type: Optional[str] = None
    class_mode: Optional[str] = None
    track_price: Optional[float] = None
    coach_price: Optional[float] = None
    total_amount: float
    coach_earnings: Optional[float] = None
    status: str
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Lessons (Coach view)
# ============================================================================


class LessonPilot(BaseModel):
    id: int
    nombre: str
    email: Optional[str] = None
    telefono: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LessonResponse(BaseModel):
    id: int
    track: TrackForReservation
    pilot: LessonPilot
    reservation_date: DateType
    start_time: TimeType
    end_time: TimeType
    participants: int
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

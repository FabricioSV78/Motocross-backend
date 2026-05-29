from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.enums import DifficultyLevel, RentalType, PilotCategory


class TrackCreate(BaseModel):
    """Schema para crear una pista (request body)."""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    price_junior: float = Field(..., gt=0)
    price_senior: float = Field(..., gt=0)
    price_junior_half: Optional[float] = Field(None, gt=0, description="Precio medio día junior (opcional)")
    price_senior_half: Optional[float] = Field(None, gt=0, description="Precio medio día senior (opcional)")
    difficulty_level: DifficultyLevel
    capacity: int = Field(..., gt=0)
    photos: Optional[List[str]] = Field(default_factory=list)

    @field_validator("photos", mode="before")
    @classmethod
    def coerce_photos(cls, v):
        return v if v is not None else []


class TrackResponse(BaseModel):
    """Schema de respuesta al crear una pista (201 Created)."""
    id: int
    name: str
    price_junior: float
    price_senior: float
    price_junior_half: Optional[float] = None
    price_senior_half: Optional[float] = None
    difficulty_level: str
    capacity: int
    company_id: int

    model_config = {"from_attributes": True}


class TrackDetail(BaseModel):
    """Schema completo de una pista (para listados o detalle)."""
    id: int
    name: str
    description: Optional[str]
    latitude: float
    longitude: float
    price_junior: float
    price_senior: float
    price_junior_half: Optional[float] = None
    price_senior_half: Optional[float] = None
    difficulty_level: str
    capacity: int
    photos: Optional[List[str]]
    schedule: Optional[List[str]] = None
    company_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TrackUpdate(BaseModel):
    """Schema para actualización parcial de pista (todos los campos opcionales)."""
    price_junior: Optional[float] = Field(None, gt=0)
    price_senior: Optional[float] = Field(None, gt=0)
    price_junior_half: Optional[float] = Field(None, gt=0)
    price_senior_half: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    schedule: Optional[List[str]] = None
    photos: Optional[List[str]] = None


class UploadTrackPhotoResponse(BaseModel):
    """URL relativa de una foto de pista subida al servidor."""
    url: str


class TrackUpdateResponse(BaseModel):
    """Schema de respuesta al actualizar una pista."""
    id: int
    name: str
    price_junior: float
    price_senior: float
    price_junior_half: Optional[float] = None
    price_senior_half: Optional[float] = None
    description: Optional[str]
    schedule: Optional[List[str]]
    photos: Optional[List[str]]

    model_config = {"from_attributes": True}


class TrackMapItem(BaseModel):
    """
    Schema optimizado para renderizar pistas en el mapa (HU-11).
    Solo contiene los campos necesarios para los markers.
    """
    id: int
    name: str
    lat: float
    lng: float
    price: float
    rating: float = 0.0
    difficulty_level: str = "BEGINNER"

    model_config = {"from_attributes": True}


# ── HU-12: Track Availability ─────────────────────────────────────────────────


class TrackAvailabilityCreate(BaseModel):
    """Request body para POST /tracks/{id}/availability."""
    date: date
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    capacity: int = Field(..., gt=0)
    rentalType: RentalType
    pilotCategory: PilotCategory = PilotCategory.BOTH

    @model_validator(mode="after")
    def validate_times(self) -> "TrackAvailabilityCreate":
        from datetime import time
        start = time.fromisoformat(self.startTime)
        end = time.fromisoformat(self.endTime)
        if start >= end:
            raise ValueError("startTime debe ser anterior a endTime")
        return self


class TrackAvailabilityResponse(BaseModel):
    """Response body para create/get availability."""
    id: int
    track_id: int
    date: date
    startTime: str
    endTime: str
    capacity: int
    rentalType: str
    pilotCategory: str = "BOTH"

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_slot(cls, slot) -> "TrackAvailabilityResponse":
        return cls(
            id=slot.id,
            track_id=slot.track_id,
            date=slot.date,
            startTime=slot.start_time.strftime("%H:%M"),
            endTime=slot.end_time.strftime("%H:%M"),
            capacity=slot.capacity,
            rentalType=slot.rental_type,
            pilotCategory=slot.pilot_category,
        )


class TrackAvailabilityCreatedResponse(BaseModel):
    message: str


class TrackAvailabilityBatchCreate(BaseModel):
    """Request body para POST /tracks/{id}/availability/batch."""
    dates: List[date] = Field(..., min_length=1, max_length=90, description="Lista de fechas (máx 90)")
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    capacity: int = Field(..., gt=0)
    rentalType: RentalType
    pilotCategory: PilotCategory = PilotCategory.BOTH

    @model_validator(mode="after")
    def validate_times(self) -> "TrackAvailabilityBatchCreate":
        from datetime import time
        start = time.fromisoformat(self.startTime)
        end = time.fromisoformat(self.endTime)
        if start >= end:
            raise ValueError("startTime debe ser anterior a endTime")
        return self


class TrackAvailabilityBatchResponse(BaseModel):
    created: int
    skipped: int
    message: str


# ── HU-17: Track Detail Public (for Pilots) ───────────────────────────────────

class CoachServiceResponse(BaseModel):
    """Servicios de un coach dentro del contexto de una pista."""
    class_type: str      # HOURLY, HALF_DAY, FULL_DAY
    mode: str            # ONE_TO_ONE, GROUP
    price: float
    max_students: int

    model_config = {"from_attributes": True}


class CoachDetailForTrack(BaseModel):
    """Coach con sus servicios, dentro del contexto de una pista."""
    id: int
    name: str
    status: str          # PENDING, APPROVED, REJECTED
    services: List[CoachServiceResponse]

    model_config = {"from_attributes": True}


class TrackDetailPublic(BaseModel):
    """
    HU-17: Respuesta pública para GET /tracks/{id}
    Incluye coaches y servicios, optimizado sin N+1 queries
    """
    id: int
    name: str
    description: Optional[str]
    latitude: float
    longitude: float
    difficulty_level: str
    photos: Optional[List[str]]
    prices: dict  # {"junior": 40, "senior": 60, "junior_half": 25, "senior_half": 35}
    coaches: List[CoachDetailForTrack]

    model_config = {"from_attributes": True}

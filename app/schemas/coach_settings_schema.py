from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.enums import ClassType, ClassMode


# ── HU-10: Settings ──────────────────────────────────────────────────────────

class TrackRef(BaseModel):
    trackId: int


class ServiceItem(BaseModel):
    classType: ClassType
    mode: ClassMode
    price: float = Field(..., gt=0, description="Price in local currency")
    maxStudents: Optional[int] = Field(None, ge=2, description="Required only for GROUP")

    @model_validator(mode="after")
    def validate_group_capacity(self) -> "ServiceItem":
        if self.mode == ClassMode.GROUP and (self.maxStudents is None or self.maxStudents < 2):
            raise ValueError("GROUP requires maxStudents >= 2")
        if self.mode == ClassMode.ONE_TO_ONE:
            self.maxStudents = 1
        return self


class CoachSettingsRequest(BaseModel):
    tracks: List[TrackRef]
    services: List[ServiceItem]


class CoachSettingsResponse(BaseModel):
    message: str


# ── HU-10: Settings response (GET) ───────────────────────────────────────────

class ServiceItemResponse(BaseModel):
    id: int
    classType: ClassType
    mode: ClassMode
    price: float
    maxStudents: int

    class Config:
        from_attributes = True


class TrackRefResponse(BaseModel):
    trackId: int
    trackName: str

    class Config:
        from_attributes = True


class CoachSettingsGetResponse(BaseModel):
    tracks: List[TrackRefResponse]
    services: List[ServiceItemResponse]


# ── HU-13: Availability ───────────────────────────────────────────────────────

class AvailabilityRequest(BaseModel):
    trackId: int
    date: date
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    classType: ClassType
    mode: ClassMode

    @model_validator(mode="after")
    def validate_times(self) -> "AvailabilityRequest":
        start = time.fromisoformat(self.startTime)
        end = time.fromisoformat(self.endTime)
        if start >= end:
            raise ValueError("startTime must be before endTime")
        return self


class AvailabilityResponse(BaseModel):
    message: str


class AvailabilityItem(BaseModel):
    id: int
    trackId: int
    trackName: str
    date: date
    startTime: str
    endTime: str
    classType: ClassType
    mode: ClassMode
    maxStudents: int

    class Config:
        from_attributes = True


class AvailabilityBatchRequest(BaseModel):
    trackId: int
    dates: List[date] = Field(..., min_length=1, max_length=90, description="List of dates (max 90)")
    startTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    endTime: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    classType: ClassType
    mode: ClassMode

    @model_validator(mode="after")
    def validate_times(self) -> "AvailabilityBatchRequest":
        start = time.fromisoformat(self.startTime)
        end = time.fromisoformat(self.endTime)
        if start >= end:
            raise ValueError("startTime must be before endTime")
        return self


class AvailabilityBatchResponse(BaseModel):
    created: int
    skipped: int
    message: str

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterCoachRequest(BaseModel):
    """Schema para registro de coach (HU-03)"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre: str = Field(..., min_length=1)
    telefono: str = Field(..., min_length=1)
    experience: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


class CoachRegisterResponse(BaseModel):
    """Respuesta después de registrar un coach"""
    id: int
    email: EmailStr
    role: str
    status: str


class CertificateUploadResponse(BaseModel):
    """Respuesta después de subir un certificado"""
    message: str

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from app.models.enums import Role, Status, PilotLevel


# Schema para registro de piloto
class RegisterRequest(BaseModel):
    """
    Schema para solicitud de registro de piloto
    Validaciones:
    - Email válido
    - Password mínimo 8 caracteres
    - Nombre requerido
    """
    email: EmailStr
    password: str = Field(..., min_length=8, description="Contraseña mínimo 8 caracteres")
    nombre: str = Field(..., min_length=1, description="Nombre del usuario")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


# Schema para registro de empresa
class RegisterCompanyRequest(BaseModel):
    """
    Schema para solicitud de registro de empresa
    Validaciones:
    - Email válido
    - Password mínimo 8 caracteres
    - Nombre de empresa requerido
    - Teléfono requerido
    """
    email: EmailStr
    password: str = Field(..., min_length=8, description="Contraseña mínimo 8 caracteres")
    nombre_empresa: str = Field(..., min_length=1, description="Nombre de la empresa")
    telefono: str = Field(..., min_length=1, description="Teléfono de contacto")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


# Schema para respuesta de usuario
class UserResponse(BaseModel):
    """
    Schema para respuesta de usuario (sin contraseña)
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    nombre: str
    role: Role
    status: Status  
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_validator('role', mode='before')
    @classmethod
    def role_to_enum(cls, v):
        if isinstance(v, str):
            return Role(v)
        return v
    
    @field_validator('status', mode='before')
    @classmethod
    def status_to_enum(cls, v):
        if isinstance(v, str):
            return Status(v)
        return v


# Schema para respuesta de empresa
class CompanyResponse(BaseModel):
    """
    Schema para respuesta de empresa (sin contraseña)
    Incluye campos específicos de empresa
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    nombre_empresa: str
    telefono: str
    role: Role
    status: Status  
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_validator('role', mode='before')
    @classmethod
    def role_to_enum(cls, v):
        if isinstance(v, str):
            return Role(v)
        return v
    
    @field_validator('status', mode='before')
    @classmethod
    def status_to_enum(cls, v):
        if isinstance(v, str):
            return Status(v)
        return v


class UserCreate(BaseModel):
    """Schema para crear usuario"""
    email: EmailStr
    nombre: str
    password: str = Field(..., min_length=8)
    role: Role = Role.PILOT
    status: Status = Status.ACTIVE
    nombre_empresa: Optional[str] = None
    telefono: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[Role] = None
    status: Optional[Status] = None


# Schemas de autenticación
class LoginRequest(BaseModel):
    """Schema para solicitud de login"""
    email: EmailStr
    password: str


class UserBasicInfo(BaseModel):
    """Schema con información básica del usuario para login"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr


class LoginResponse(BaseModel):
    """Schema para respuesta de login"""
    token: str
    user: UserBasicInfo
    role: Role
    status: str


class Token(BaseModel):
    """Schema para respuesta de login OAuth2"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Schema para payload del JWT"""
    sub: Optional[int] = None


class LogoutResponse(BaseModel):
    """Schema para respuesta de logout"""
    message: str


# Schemas de perfil de piloto
class PilotProfileResponse(BaseModel):
    """Schema para respuesta de perfil de piloto"""
    model_config = ConfigDict(from_attributes=True)
    
    foto: Optional[str] = None
    nivel: PilotLevel
    moto: Optional[str] = None
    
    @field_validator('nivel', mode='before')
    @classmethod
    def nivel_to_enum(cls, v):
        if isinstance(v, str):
            return PilotLevel(v)
        return v


class UploadPhotoResponse(BaseModel):
    """Schema para respuesta de subida de foto"""
    url: str


class UserProfileResponse(BaseModel):
    """
    Schema para respuesta de perfil completo de usuario piloto
    HU-05: Ver perfil
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    nombre: str
    foto: Optional[str] = None
    foto_moto: Optional[str] = None
    nivel: PilotLevel
    moto: Optional[str] = None
    
    @field_validator('nivel', mode='before')
    @classmethod
    def nivel_to_enum(cls, v):
        if isinstance(v, str):
            return PilotLevel(v)
        return v


class PilotProfileCreate(BaseModel):
    """Schema para crear perfil de piloto"""
    foto: Optional[str] = None
    nivel: PilotLevel = PilotLevel.BEGINNER
    moto: Optional[str] = None


class UpdateUserProfileRequest(BaseModel):
    """
    Schema para actualizar perfil completo del piloto
    HU-06: Editar perfil
    """
    nombre: str = Field(..., min_length=1, description="Nombre del usuario")
    foto: Optional[str] = None
    foto_moto: Optional[str] = None
    nivel: Optional[PilotLevel] = None
    moto: Optional[str] = None

    @field_validator('nivel', mode='before')
    @classmethod
    def nivel_to_enum(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return PilotLevel(v)
        return v

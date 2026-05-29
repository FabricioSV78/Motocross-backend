from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.models.enums import Role, Status


class CompanyListItem(BaseModel):
    """Schema para un item de empresa en listados"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str
    nombre_empresa: Optional[str] = None
    telefono: Optional[str] = None
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


class ApproveCompanyResponse(BaseModel):
    """Schema de respuesta para aprobar empresa"""
    message: str
    companyId: int
    status: str

from typing import Literal, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# HU-25: Verificar proveedor (aprobar / rechazar)
# ---------------------------------------------------------------------------

class VerifyProviderRequest(BaseModel):
    """Body del endpoint PUT /admin/verify-provider/{id}"""
    providerType: Literal["COACH", "COMPANY"]
    status: Literal["APPROVED", "REJECTED"]


class VerifyProviderResponse(BaseModel):
    """Respuesta del endpoint PUT /admin/verify-provider/{id}"""
    message: str
    providerId: int
    providerType: str
    status: str


# ---------------------------------------------------------------------------
# HU-25: Listado de proveedores pendientes
# ---------------------------------------------------------------------------

class PendingProviderItem(BaseModel):
    """Item unificado en el listado de proveedores pendientes"""
    id: int          # user_id (COMPANY) o user_id del coach (COACH)
    name: str
    email: str
    type: str        # "COACH" | "COMPANY"
    status: str
    certificate_url: Optional[str] = None  # Solo para COACH

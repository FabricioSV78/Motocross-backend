from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session
from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.models.enums import Status
from app.schemas.company_schema import CompanyListItem, ApproveCompanyResponse
from app.schemas.admin_schema import VerifyProviderRequest, VerifyProviderResponse, PendingProviderItem
from app.services.admin_service import AdminService

router = APIRouter()


@router.get(
    "/companies",
    response_model=List[CompanyListItem],
    summary="Listar empresas",
    description="Obtiene la lista de empresas. Solo accesible por ADMIN.",
)
def list_companies(
    status_query: Optional[str] = Query(
        None,
        alias="status",
        description="Filtrar por estado: PENDING, APPROVED, REJECTED, etc.",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Listar empresas, opcionalmente filtradas por status. Requiere rol ADMIN."""
    service = AdminService(db)

    status_filter: Optional[Status] = None
    if status_query:
        try:
            status_filter = Status(status_query.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_query}. Valores permitidos: {[s.value for s in Status]}",
            )

    return service.get_companies(status_filter)


@router.put(
    "/companies/{company_id}/approve",
    response_model=ApproveCompanyResponse,
    summary="Aprobar empresa",
    description="Cambia el status de una empresa a APPROVED. Solo accesible por ADMIN.",
)
def approve_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    HU-24: Aprobar empresa.
    - Requiere rol ADMIN (403 si no lo es)
    - 404 si la empresa no existe
    - 400 si ya está aprobada
    - 200 con { message, companyId, status } si éxito
    """
    service = AdminService(db)
    company = service.approve_company(company_id)
    return ApproveCompanyResponse(
        message="Company approved",
        companyId=company.id,
        status="APPROVED",
    )


# ---------------------------------------------------------------------------
# HU-25: Listar proveedores (con filtro opcional de status)
# ---------------------------------------------------------------------------

@router.get(
    "/providers",
    response_model=List[PendingProviderItem],
    summary="Listar proveedores",
    description="Obtiene coaches y empresas. Filtra por ?status=PENDING|APPROVED|REJECTED o devuelve todos. Solo ADMIN.",
)
def list_providers(
    status_query: Optional[str] = Query(
        None,
        alias="status",
        description="Filtrar por estado: PENDING, APPROVED, REJECTED",
    ),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """HU-25: Lista proveedores con filtro opcional de status."""
    service = AdminService(db)
    status_filter: Optional[Status] = None
    if status_query:
        try:
            status_filter = Status(status_query.upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {status_query}. Valores permitidos: {[s.value for s in Status]}",
            )
    return service.get_providers(status_filter)


# ---------------------------------------------------------------------------
# HU-25: Verificar proveedor (aprobar / rechazar)
# ---------------------------------------------------------------------------

@router.put(
    "/verify-provider/{provider_id}",
    response_model=VerifyProviderResponse,
    summary="Aprobar o rechazar un proveedor",
    description="Cambia el status de un COACH o COMPANY a APPROVED o REJECTED. Solo ADMIN.",
)
def verify_provider(
    provider_id: int,
    body: VerifyProviderRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    HU-25: Verificar proveedor.
    - 401 si no autenticado
    - 403 si no es ADMIN
    - 404 si el proveedor no existe
    - 400 si providerType inválido
    - 200 con { message, providerId, providerType, status } si éxito
    """
    service = AdminService(db)
    result = service.verify_provider(
        provider_id=provider_id,
        provider_type=body.providerType,
        new_status=body.status,
    )
    return VerifyProviderResponse(**result)

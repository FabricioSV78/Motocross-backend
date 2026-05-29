from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.company_repository import CompanyRepository
from app.repositories.coach_repository import CoachRepository
from app.models.user import User
from app.models.enums import Status, Role
from app.schemas.admin_schema import PendingProviderItem


class AdminService:
    """
    Servicio de lógica de negocio para operaciones de administración.
    """

    def __init__(self, db: Session):
        self.repo = CompanyRepository(db)
        self.coach_repo = CoachRepository(db)

    def get_companies(self, status_filter: Optional[Status] = None) -> List[User]:
        """
        Obtener lista de empresas, opcionalmente filtradas por estado.

        Args:
            status_filter: Status enum para filtrar (ej: PENDING, APPROVED)

        Returns:
            Lista de usuarios con role = COMPANY
        """
        if status_filter is not None:
            return self.repo.get_by_status(status_filter)
        return self.repo.get_all()

    def approve_company(self, company_id: int) -> User:
        """
        Aprobar una empresa cambiando su status a APPROVED.

        Args:
            company_id: ID de la empresa a aprobar

        Returns:
            Empresa actualizada

        Raises:
            HTTPException 404 si la empresa no existe
            HTTPException 400 si la empresa ya está aprobada
        """
        company = self.repo.get_by_id(company_id)

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with id {company_id} not found",
            )

        if company.status == Status.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company is already approved",
            )

        return self.repo.approve(company)

    # -----------------------------------------------------------------------
    # HU-25: Verificar proveedor (aprobar / rechazar)
    # -----------------------------------------------------------------------

    def verify_provider(self, provider_id: int, provider_type: str, new_status: str) -> dict:
        """
        Aprobar o rechazar un proveedor (COACH o COMPANY).

        Args:
            provider_id: User ID del proveedor
            provider_type: "COACH" | "COMPANY"
            new_status: "APPROVED" | "REJECTED"

        Returns:
            dict con providerId, providerType y status actualizados
        """
        try:
            target_status = Status(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}",
            )

        if provider_type == "COMPANY":
            provider = self.repo.get_by_id_any_status(provider_id)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with id {provider_id} not found",
                )
            if target_status == Status.APPROVED:
                self.repo.approve(provider)
            else:
                self.repo.reject(provider)

        elif provider_type == "COACH":
            coach = self.coach_repo.update_status_by_user_id(provider_id, target_status)
            if not coach:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Coach with user_id {provider_id} not found",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider type: {provider_type}. Allowed values: COACH, COMPANY",
            )

        return {
            "message": "Provider status updated",
            "providerId": provider_id,
            "providerType": provider_type,
            "status": new_status,
        }

    def get_providers(self, status_filter: Optional[Status] = None) -> List[PendingProviderItem]:
        """
        Obtener lista unificada de proveedores (COACH + COMPANY).
        Si status_filter es None devuelve todos; si no, filtra por ese status.
        """
        items: List[PendingProviderItem] = []

        # --- Empresas ---
        companies = (
            self.repo.get_by_status(status_filter)
            if status_filter
            else self.repo.get_all()
        )
        for company in companies:
            items.append(
                PendingProviderItem(
                    id=company.id,
                    name=company.nombre_empresa or company.nombre or f"Company #{company.id}",
                    email=company.email,
                    type="COMPANY",
                    status=company.status,
                )
            )

        # --- Coaches ---
        coaches = (
            self.coach_repo.get_by_status(status_filter)
            if status_filter
            else self.coach_repo.get_all()
        )
        for coach in coaches:
            user: User = coach.user
            items.append(
                PendingProviderItem(
                    id=user.id,
                    name=user.nombre or f"Coach #{user.id}",
                    email=user.email,
                    type="COACH",
                    status=coach.status,
                    certificate_url=coach.certificate_url,
                )
            )

        return items

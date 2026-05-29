from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.track import Track
from app.models.enums import Role
from app.repositories.tracks_repository import TracksRepository


class CompanyTracksService:
    """
    Servicio para que una empresa consulte sus propias pistas.
    Lógica de negocio de HU-10.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = TracksRepository(db)

    def get_my_tracks(self, current_user: User) -> List[Track]:
        """
        Devuelve las pistas que pertenecen a la empresa autenticada.

        Reglas de negocio:
        - Solo usuarios con rol COMPANY pueden ver sus pistas.

        Args:
            current_user: Usuario autenticado obtenido del JWT.

        Returns:
            Lista de pistas de la empresa, ordenadas por created_at DESC.

        Raises:
            HTTPException 403: Si el usuario no tiene rol COMPANY.
        """
        if current_user.role != Role.COMPANY.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only companies can access this resource",
            )

        return self.repo.get_by_company(company_id=current_user.id)

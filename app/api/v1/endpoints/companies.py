from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.track_schema import TrackDetail
from app.services.company_tracks_service import CompanyTracksService

router = APIRouter()


@router.get(
    "/tracks",
    response_model=List[TrackDetail],
    summary="Listar mis pistas",
    description=(
        "Devuelve las pistas que pertenecen a la empresa autenticada, "
        "ordenadas de más reciente a más antigua. Solo accesible por COMPANY."
    ),
)
def get_my_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    HU-10: Ver pistas de empresa.
    - 403 si el usuario no tiene rol COMPANY.
    - 200 con lista (vacía si aún no tiene pistas).
    """
    service = CompanyTracksService(db)
    return service.get_my_tracks(current_user)

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_company
from app.core.config import UPLOAD_DIR
from app.db.session import get_db
from app.models.user import User
from app.schemas.track_schema import (
    TrackCreate,
    TrackResponse,
    TrackDetail,
    TrackUpdate,
    TrackUpdateResponse,
    TrackMapItem,
    TrackDetailPublic,
    TrackAvailabilityCreate,
    TrackAvailabilityCreatedResponse,
    TrackAvailabilityBatchCreate,
    TrackAvailabilityBatchResponse,
    TrackAvailabilityResponse,
    UploadTrackPhotoResponse,
)
from app.services.tracks_service import TracksService

TRACKS_UPLOAD_DIR = UPLOAD_DIR / "tracks"

router = APIRouter()


@router.get(
    "",
    response_model=List[TrackMapItem],
    summary="Listar pistas para el mapa",
    description=(
        "Endpoint público (no requiere login). "
        "Devuelve las pistas de empresas APPROVED con los datos mínimos para renderizar markers en el mapa."
    ),
    tags=["Mapa"],
)
def get_tracks_map(db: Session = Depends(get_db)):
    """HU-11: Ver mapa de pistas."""
    service = TracksService(db)
    return service.get_map_tracks()


@router.get(
    "/detail/{track_id}",
    response_model=TrackDetailPublic,
    summary="Obtener detalle de pista",
    description=(
        "HU-17: Endpoint público (no requiere login). "
        "Devuelve información completa de una pista incluyendo coaches y servicios. "
        "Solo coaches con status APPROVED se incluyen."
    ),
    tags=["Detalles Públicos"],
)
def get_track_detail(track_id: int, db: Session = Depends(get_db)):
    """HU-17: Ver detalles de una pista con coaches."""
    service = TracksService(db)
    return service.get_track_detail_public(track_id)


@router.post(
    "",
    response_model=TrackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pista",
    description="Crea una nueva pista de motocross. Solo accesible por empresas con status APPROVED.",
)
def create_track(
    track_in: TrackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """HU-08: Crear pista."""
    service = TracksService(db)
    return service.create_track(track_in, current_user)


@router.post(
    "/upload-photo",
    response_model=UploadTrackPhotoResponse,
    summary="Subir foto de pista",
    description="Sube una imagen desde el dispositivo. Solo empresas aprobadas.",
)
async def upload_track_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_company),
):
    """Guarda imagen en /uploads/tracks/ y devuelve ruta relativa para el campo photos."""
    _ = current_user
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPG, PNG or WebP images are allowed.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5 MB.")

    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"track_{uuid.uuid4().hex[:12]}.{ext}"

    TRACKS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    from app.services.storage_service import storage_service

    if storage_service.enabled:
        key = f"tracks/{filename}"
        public_url = storage_service.upload_bytes(key, contents, content_type=file.content_type)
        return UploadTrackPhotoResponse(url=public_url)
    else:
        with open(TRACKS_UPLOAD_DIR / filename, "wb") as fp:
            fp.write(contents)

        relative_url = f"/uploads/tracks/{filename}"
        return UploadTrackPhotoResponse(url=relative_url)


@router.get(
    "/{track_id}",
    response_model=TrackDetail,
    summary="Obtener pista por ID",
    description="Devuelve los datos de una pista. Solo la empresa dueña puede consultarla para edición.",
)
def get_track(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """HU-09: Cargar datos actuales de la pista en el formulario de edición."""
    service = TracksService(db)
    return service.get_track(track_id, current_user)


@router.put(
    "/{track_id}",
    response_model=TrackUpdateResponse,
    summary="Editar pista",
    description=(
        "Actualiza parcialmente los campos editables de una pista (precio, descripción, "
        "horarios, fotos). Solo la empresa dueña puede editarla."
    ),
)
def update_track(
    track_id: int,
    track_in: TrackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    HU-09: Editar pista.
    - 403 si el usuario no tiene rol COMPANY.
    - 403 si la pista pertenece a otra empresa.
    - 404 si la pista no existe.
    - 200 con los campos actualizados.
    """
    service = TracksService(db)
    return service.update_track(track_id, track_in, current_user)


@router.post(
    "/{track_id}/availability",
    response_model=TrackAvailabilityCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear disponibilidad de pista",
    description=(
        "HU-12: Define una franja horaria disponible para una pista. "
        "Solo la empresa propietaria puede crear disponibilidad. "
        "Valida solapamiento de horarios en la misma fecha."
    ),
)
def create_track_availability(
    track_id: int,
    body: TrackAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_company),
):
    """
    HU-12: Definir disponibilidad de una pista.

    - 201: Disponibilidad creada.
    - 403: No eres el propietario de la pista o no eres empresa aprobada.
    - 404: Pista no encontrada.
    - 409: El horario se solapa con una disponibilidad existente.
    - 422: startTime >= endTime.
    """
    service = TracksService(db)
    return service.create_track_availability(track_id, body, current_user)


@router.post(
    "/{track_id}/availability/batch",
    response_model=TrackAvailabilityBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear disponibilidad en lote",
    description=(
        "HU-12: Crea múltiples slots de disponibilidad para una pista a partir de una lista "
        "de fechas. Los slots que se solapen con existentes se omiten (no generan error)."
    ),
)
def create_track_availability_batch(
    track_id: int,
    body: TrackAvailabilityBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_company),
):
    service = TracksService(db)
    return service.create_track_availability_batch(track_id, body, current_user)


@router.get(
    "/{track_id}/availability",
    response_model=List[TrackAvailabilityResponse],
    summary="Listar disponibilidades de una pista",
    description="Devuelve todos los slots de disponibilidad futuros de una pista. Solo la empresa propietaria puede consultarlos.",
)
def get_track_availability(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_company),
):
    service = TracksService(db)
    return service.get_track_availability(track_id, current_user)


@router.get(
    "/{track_id}/available-slots",
    response_model=List[TrackAvailabilityResponse],
    summary="Obtener slots disponibles para una fecha (público)",
    description=(
        "Endpoint público que devuelve los slots de disponibilidad de una pista "
        "para una fecha específica. Útil para el checkout del piloto."
    ),
    tags=["Detalles Públicos"],
)
def get_available_slots_for_date(
    track_id: int,
    date: str,  # Formato: YYYY-MM-DD
    db: Session = Depends(get_db),
):
    """
    Obtener los slots disponibles de una pista para una fecha específica.
    No requiere autenticación (endpoint público).
    
    - 200: Lista de slots disponibles
    - 404: Pista no encontrada
    - 400: Fecha inválida
    """
    service = TracksService(db)
    return service.get_available_slots_for_date(track_id, date)


@router.get(
    "/{track_id}/available-dates",
    response_model=List[dict],
    summary="Obtener fechas con disponibilidad (público)",
    description=(
        "Endpoint público que devuelve las FECHAS que tienen slots disponibles para una pista. "
        "Útil para mostrar un calendario solo con fechas disponibles en el checkout."
    ),
    tags=["Detalles Públicos"],
)
def get_available_dates(
    track_id: int,
    start_date: str = None,  # Formato: YYYY-MM-DD (opcional)
    end_date: str = None,    # Formato: YYYY-MM-DD (opcional)
    db: Session = Depends(get_db),
):
    """
    Obtener las fechas disponibles de una pista con los slots para cada fecha.
    No requiere autenticación (endpoint público).
    
    Returns: [{'date': 'YYYY-MM-DD', 'slots': [{'startTime': 'HH:MM', 'endTime': 'HH:MM'}, ...]}, ...]
    
    - 200: Lista de fechas con slots
    - 404: Pista no encontrada
    - 400: Fechas inválidas
    """
    from datetime import datetime
    from fastapi import Query
    from app.repositories.tracks_repository import TracksRepository
    
    repo = TracksRepository(db)
    
    # Validar track existe
    track = repo.get_by_id(track_id)
    if not track:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Parsear fechas opcionales
    start = None
    end = None
    try:
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    dates_with_slots = repo.get_available_dates(track_id, start, end)
    return dates_with_slots

from fastapi import APIRouter, Depends, File, UploadFile, status, Query, HTTPException
from typing import List, Optional
from datetime import date, datetime
import logging
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.coach import CertificateUploadResponse
from app.schemas.coach_settings_schema import (
    CoachSettingsRequest,
    CoachSettingsResponse,
    CoachSettingsGetResponse,
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilityItem,
    AvailabilityBatchRequest,
    AvailabilityBatchResponse,
)
from app.services.coach_service import CoachService
from app.services.coach_settings_service import CoachSettingsService
from app.repositories.coach_settings_repository import CoachSettingsRepository
from app.repositories.reservation_repository import ReservationRepository
from app.api.deps import get_current_coach
from app.models.user import User
from app.repositories.coach_repository import CoachRepository
from app.services.reservation_service import ReservationService
from app.schemas.reservation_schema import LessonResponse

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/certificate", response_model=CertificateUploadResponse)
async def upload_certificate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    """
    HU-09: Subir certificado de coach

    Permite al coach autenticado subir su certificado para demostrar
    que puede enseñar motocross. El archivo queda en estado PENDING_REVIEW.

    Requiere autenticación JWT.
    Solo usuarios con role = COACH pueden usar este endpoint.

    Form-data:
    - **file**: Archivo PDF o imagen (JPG, PNG, WebP). Máximo 5 MB.

    Returns:
        Mensaje de confirmación.

    Raises:
        400: Formato de archivo no válido
        401: No autenticado
        403: El usuario no es coach
        404: Perfil de coach no encontrado
        413: Archivo supera 5 MB
        500: Error del servidor
    """
    coach_service = CoachService(db)
    message = await coach_service.upload_certificate(current_user.id, file)
    return CertificateUploadResponse(message=message)


# ── HU-10: Coach settings ─────────────────────────────────────────────────────

@router.put("/settings", response_model=CoachSettingsResponse)
def update_coach_settings(
    body: CoachSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    """
    HU-10: Configurar pistas, servicios y precios del coach.

    Reemplaza la lista completa de pistas habilitadas y servicios ofrecidos.
    Requiere autenticación JWT con role = COACH.

    Body:
    - **tracks**: Lista de {trackId} donde el coach puede impartir clases
    - **services**: Lista de servicios con classType, mode, price y maxStudents

    Returns:
        Mensaje de confirmación.

    Raises:
        401: No autenticado
        403: El usuario no es coach
        404: Perfil de coach o pista no encontrado
    """
    svc = CoachSettingsService(CoachSettingsRepository(db))
    return svc.update_settings(current_user.id, body)


@router.get("/settings", response_model=CoachSettingsGetResponse)
def get_coach_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    """
    HU-10: Obtener configuración actual del coach.

    Devuelve pistas y servicios configurados por el coach autenticado.

    Returns:
        tracks: lista de pistas con id y nombre
        services: lista de servicios configurados

    Raises:
        401: No autenticado
        403: El usuario no es coach
        404: Perfil de coach no encontrado
    """
    svc = CoachSettingsService(CoachSettingsRepository(db))
    return svc.get_settings(current_user.id)


# ── HU-13: Coach availability ─────────────────────────────────────────────────

@router.post("/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
def create_availability(
    body: AvailabilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    """
    HU-13: Registrar disponibilidad del coach.

    Crea un slot de disponibilidad para una pista y fecha específica.
    Valida que no se solape con otro slot existente el mismo día.

    Body:
    - **trackId**: ID de la pista donde estará disponible
    - **date**: Fecha (YYYY-MM-DD)
    - **startTime**: Hora de inicio (HH:MM)
    - **endTime**: Hora de fin (HH:MM)

    Returns:
        Mensaje de confirmación.

    Raises:
        401: No autenticado
        403: El usuario no es coach
        404: Pista o perfil de coach no encontrado
        409: El slot se solapa con una disponibilidad existente
    """
    svc = CoachSettingsService(CoachSettingsRepository(db))
    return svc.create_availability(current_user.id, body)


@router.get("/availability", response_model=List[AvailabilityItem])
def get_availability(
    from_date: Optional[date] = Query(
        default=None,
        description="Filtrar slots desde esta fecha. Por defecto: hoy (no muestra pasados).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    svc = CoachSettingsService(CoachSettingsRepository(db))
    return svc.get_availability(current_user.id, from_date=from_date)


@router.post(
    "/availability/batch",
    response_model=AvailabilityBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar disponibilidad en lote",
    description=(
        "Crea múltiples slots de disponibilidad para el coach a partir de una lista de fechas. "
        "Los slots que se solapen con existentes se omiten automáticamente."
    ),
)
def create_availability_batch(
    body: AvailabilityBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    svc = CoachSettingsService(CoachSettingsRepository(db))
    return svc.create_availability_batch(current_user.id, body)


# ── PUBLIC ENDPOINTS ──────────────────────────────────────────────────────────

@router.get(
    "/{coach_id}/available-slots",
    response_model=List[AvailabilityItem],
    summary="Obtener slots disponibles del coach (público)",
    description=(
        "Endpoint público que devuelve los slots de disponibilidad de un coach "
        "para una fecha y pista específica. Útil para el checkout del piloto."
    ),
    tags=["Detalles Públicos"],
)
def get_coach_available_slots(
    coach_id: int,
    track_id: int = Query(..., description="ID de la pista"),
    date: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD (opcional)"),
    db: Session = Depends(get_db),
):
    """
    Obtener los slots disponibles de un coach para una pista y fecha específica.
    No requiere autenticación (endpoint público).
    
    - 200: Lista de slots disponibles
    - 404: Coach o pista no encontrado
    - 400: Fecha inválida
    """
    logger.info(f"[DEBUG] GET /coach/{coach_id}/available-slots?track_id={track_id}&date={date}")
    
    repo = CoachSettingsRepository(db)
    track = repo.get_track_by_id(track_id)
    if not track:
        logger.warning(f"[DEBUG] Track no encontrada: {track_id}")
        raise HTTPException(status_code=404, detail="Track not found")
    
    logger.info(f"[DEBUG] Track encontrada: {track.name} (id={track_id})")
    
    if date:
        try:
            date_val = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"[DEBUG] Fecha inválida: {date}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
        # Obtener slots para esa fecha específica
        slots = repo.get_availability_by_coach_track_and_date(coach_id, track_id, date_val)
        logger.info(f"[DEBUG] Slots para coach {coach_id}, track {track_id}, date {date_val}: {len(slots)} encontrados")
    else:
        # Obtener todos los slots futuros
        from datetime import date as date_type
        today = date_type.today()
        all_slots = repo.get_availability_by_coach_and_track(coach_id, track_id)
        slots = [s for s in all_slots if s.date >= today]
        logger.info(f"[DEBUG] Slots futuros para coach {coach_id}, track {track_id}: {len(slots)} encontrados")
    
    if not slots:
        logger.warning(f"[DEBUG] No hay slots disponibles. Coach: {coach_id}, Track: {track_id}, Date: {date}")
        return []
    
    # Convertir a AvailabilityItem
    items = []
    for slot in slots:
        logger.debug(f"[DEBUG] Procesando slot: {slot.date} {slot.start_time}-{slot.end_time} ({slot.class_type}/{slot.mode})")
        coach_service = repo.get_coach_service(coach_id, slot.class_type, slot.mode)
        # Si no hay servicio configurado para este tipo/modalidad, omitimos el slot
        if not coach_service:
            logger.debug(f"[DEBUG] Coach service not configured for slot {slot.id}, skipping")
            continue

        max_students = coach_service.max_students if coach_service else 1

        # Verificar reservas superpuestas del coach para este slot
        overlaps = ReservationRepository.get_coach_reservations_overlap(
            db, coach_id, slot.date, slot.start_time, slot.end_time
        )

        # Si el servicio es ONE_TO_ONE y hay cualquier reserva superpuesta, excluir el slot
        if coach_service.mode == 'ONE_TO_ONE' and overlaps:
            logger.debug(f"[DEBUG] ONE_TO_ONE slot {slot.id} ocupado por otra reserva, omitiendo")
            continue

        # Si el servicio es GROUP, sumar participantes ya reservados y comparar con max_students
        if coach_service.mode == 'GROUP' and overlaps:
            total_booked = sum(r.participants for r in overlaps)
            if total_booked >= max_students:
                logger.debug(f"[DEBUG] GROUP slot {slot.id} lleno ({total_booked}/{max_students}), omitiendo")
                continue

        items.append(
            AvailabilityItem(
                id=slot.id,
                trackId=slot.track_id,
                trackName=track.name,
                date=slot.date,
                startTime=slot.start_time.strftime("%H:%M"),
                endTime=slot.end_time.strftime("%H:%M"),
                classType=slot.class_type,
                mode=slot.mode,
                maxStudents=max_students,
            )
        )
    
    logger.info(f"[DEBUG] Devolviendo {len(items)} items al cliente")
    return items



@router.get("/lessons", response_model=list[LessonResponse])
def get_coach_lessons(
    from_date: Optional[date] = Query(default=None, description="Filtrar lecciones desde esta fecha (YYYY-MM-DD)."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_coach),
):
    """
    Obtener las lecciones (reservas) asociadas al coach autenticado.

    - Solo accesible por usuarios con role = COACH (depende de `get_current_coach`).
    - Devuelve reservas filtradas por fecha (si se provee `from_date`) o futuras por defecto.
    """
    coach_repo = CoachRepository(db)
    coach = coach_repo.get_by_user_id(current_user.id)
    if not coach:
        raise HTTPException(status_code=404, detail="Perfil de coach no encontrado")

    reservations = ReservationService.get_coach_reservations(db, coach.id)

    # Filtrar por fecha si se indicó
    from datetime import date as date_type
    today = date_type.today()
    if from_date:
        try:
            # if from_date provided as date object by FastAPI it stays as date
            cutoff = from_date
        except Exception:
            cutoff = today
    else:
        cutoff = today

    result = []
    for res in reservations:
        if res.reservation_date < cutoff:
            continue

        result.append(
            LessonResponse(
                id=res.id,
                track={
                    "id": res.track.id,
                    "name": res.track.name,
                    "location": f"{res.track.latitude},{res.track.longitude}",
                },
                pilot={
                    "id": res.user.id,
                    "nombre": res.user.nombre,
                    "email": res.user.email,
                    "telefono": res.user.telefono,
                },
                reservation_date=res.reservation_date,
                start_time=res.start_time,
                end_time=res.end_time,
                participants=res.participants,
                status=res.status,
                created_at=res.created_at.isoformat(),
            )
        )

    return result

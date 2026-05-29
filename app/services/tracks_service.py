from typing import List
from datetime import time, date as date_type
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.track import Track
from app.models.enums import Role, Status
from app.schemas.track_schema import (
    TrackCreate, TrackUpdate, TrackMapItem, TrackDetailPublic,
    TrackAvailabilityCreate, TrackAvailabilityCreatedResponse,
    TrackAvailabilityBatchCreate, TrackAvailabilityBatchResponse,
    TrackAvailabilityResponse,
)
from app.repositories.tracks_repository import TracksRepository


class TracksService:
    """
    Servicio de pistas.
    Contiene toda la lógica de negocio para la gestión de pistas.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = TracksRepository(db)

    def _require_company(self, user: User) -> None:
        if user.role != Role.COMPANY.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only companies can perform this action",
            )

    def _get_owned_track(self, track_id: int, current_user: User) -> Track:
        """Obtiene la pista, validando existencia y ownership."""
        track = self.repo.get_by_id(track_id)
        if track is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found",
            )
        if track.company_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this track",
            )
        return track

    def create_track(self, track_data: TrackCreate, current_user: User) -> Track:
        """
        Crear una pista.
        - Solo COMPANY con status APPROVED puede crear pistas.
        """
        self._require_company(current_user)

        if current_user.status != Status.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your company is not approved to create tracks yet",
            )

        return self.repo.create(track_data, company_id=current_user.id)

    def get_track(self, track_id: int, current_user: User) -> Track:
        """
        Obtener una pista por ID.
        - Solo COMPANY puede acceder (para el formulario de edición).
        - Valida ownership.
        """
        self._require_company(current_user)
        return self._get_owned_track(track_id, current_user)

    def update_track(self, track_id: int, update_data: TrackUpdate, current_user: User) -> Track:
        """
        Actualizar una pista (partial update).
        - Solo COMPANY puede editar.
        - Solo la empresa dueña puede editar su pista.
        """
        self._require_company(current_user)
        track = self._get_owned_track(track_id, current_user)
        return self.repo.update(track, update_data)

    def get_map_tracks(self) -> List[TrackMapItem]:
        """
        HU-11: Pistas para el mapa público.
        - Solo pistas de empresas con status APPROVED.
        - Rating = 0 hasta que exista el modelo de reviews.
        """
        tracks = self.repo.get_tracks_for_map()
        return [
            TrackMapItem(
                id=t.id,
                name=t.name,
                lat=t.latitude,
                lng=t.longitude,
                price=t.price_junior,
                rating=0.0,
                difficulty_level=t.difficulty_level,
            )
            for t in tracks
        ]

    def get_track_detail_public(self, track_id: int):
        """
        HU-17: Obtener detalles públicos de una pista con coaches.
        - Devuelve: info básica + lista de coaches y sus servicios
        - Solo pistas de empresas APPROVED
        - Solo coaches APPROVED
        - Endpoint público (sin autenticación)
        """
        from app.schemas.track_schema import TrackDetailPublic, CoachDetailForTrack, CoachServiceResponse

        track = self.repo.get_track_with_coaches(track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found",
            )

        # Construir lista de coaches con servicios (solo APPROVED)
        coaches_list = []
        for coach_track in track.coach_tracks or []:
            coach = coach_track.coach
            if coach.status != Status.APPROVED.value:
                continue

            # Construir lista de servicios
            services = [
                CoachServiceResponse(
                    class_type=svc.class_type,
                    mode=svc.mode,
                    price=svc.price,
                    max_students=svc.max_students,
                )
                for svc in coach.services
            ]

            coaches_list.append(
                CoachDetailForTrack(
                    id=coach.id,
                    name=coach.user.nombre,
                    status=coach.status,
                    services=services,
                )
            )

        # Construir precios
        prices = {
            "junior": track.price_junior,
            "senior": track.price_senior,
        }
        if track.price_junior_half:
            prices["junior_half"] = track.price_junior_half
        if track.price_senior_half:
            prices["senior_half"] = track.price_senior_half

        return TrackDetailPublic(
            id=track.id,
            name=track.name,
            description=track.description,
            latitude=track.latitude,
            longitude=track.longitude,
            difficulty_level=track.difficulty_level,
            photos=track.photos or [],
            prices=prices,
            coaches=coaches_list,
        )

    # ── HU-12: Track Availability ─────────────────────────────────────────────

    def create_track_availability(
        self,
        track_id: int,
        req: TrackAvailabilityCreate,
        current_user: User,
    ) -> TrackAvailabilityCreatedResponse:
        """
        HU-12: Definir disponibilidad de una pista.
        - Solo el propietario de la pista puede crear disponibilidad.
        - startTime < endTime (validado en schema).
        - No se permite solapamiento de franjas el mismo día.
        """
        self._require_company(current_user)
        track = self._get_owned_track(track_id, current_user)

        start = time.fromisoformat(req.startTime)
        end = time.fromisoformat(req.endTime)

        overlap = self.repo.get_overlapping_availability(
            track_id=track.id,
            date_val=req.date,
            start=start,
            end=end,
        )
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This time slot overlaps with existing availability for this track.",
            )

        self.repo.create_availability(
            track_id=track.id,
            date_val=req.date,
            start=start,
            end=end,
            capacity=req.capacity,
            rental_type=req.rentalType.value,
            pilot_category=req.pilotCategory.value,
        )
        return TrackAvailabilityCreatedResponse(message="Track availability created")

    def create_track_availability_batch(
        self,
        track_id: int,
        req: TrackAvailabilityBatchCreate,
        current_user: User,
    ) -> TrackAvailabilityBatchResponse:
        """
        HU-12: Crear disponibilidad en lote para una pista.
        - Omite fechas que se solapan con slots existentes (sin error, solo skipped).
        """
        self._require_company(current_user)
        track = self._get_owned_track(track_id, current_user)

        start = time.fromisoformat(req.startTime)
        end = time.fromisoformat(req.endTime)

        to_create = []
        skipped = 0
        for d in req.dates:
            overlap = self.repo.get_overlapping_availability(
                track_id=track.id, date_val=d, start=start, end=end
            )
            if overlap:
                skipped += 1
            else:
                to_create.append(d)

        self.repo.create_availability_batch(
            track_id=track.id,
            dates=to_create,
            start=start,
            end=end,
            capacity=req.capacity,
            rental_type=req.rentalType.value,
            pilot_category=req.pilotCategory.value,
        )
        created = len(to_create)
        return TrackAvailabilityBatchResponse(
            created=created,
            skipped=skipped,
            message=f"{created} availability slot(s) created, {skipped} skipped due to overlaps.",
        )

    def get_track_availability(
        self,
        track_id: int,
        current_user: User,
    ) -> List[TrackAvailabilityResponse]:
        """HU-12: Listar disponibilidades futuras de una pista (solo el propietario)."""
        self._require_company(current_user)
        self._get_owned_track(track_id, current_user)
        today = date_type.today()
        slots = [
            s for s in self.repo.get_availability_by_track(track_id)
            if s.date >= today
        ]
        return [TrackAvailabilityResponse.from_orm_slot(s) for s in slots]

    def get_available_slots_for_date(self, track_id: int, date_str: str) -> List[TrackAvailabilityResponse]:
        """
        Obtener los slots disponibles de una pista para una fecha específica (endpoint público).
        Devuelve una lista vacía si no hay slots disponibles o la pista no existe.
        
        Args:
            track_id: ID de la pista
            date_str: Fecha en formato YYYY-MM-DD
        
        Returns:
            Lista de slots disponibles para esa fecha
        """
        # Validar que la pista exista
        track = self.repo.get_by_id(track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Track not found",
            )

        # Parsear la fecha
        try:
            from datetime import datetime
            date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )

        # Obtener slots para esa fecha
        slots = self.repo.get_availability_by_track_and_date(track_id, date_val)
        return [TrackAvailabilityResponse.from_orm_slot(s) for s in slots]

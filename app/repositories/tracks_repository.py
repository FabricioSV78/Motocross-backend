from typing import List, Optional
from datetime import date, time
from sqlalchemy.orm import Session
from app.models.track import Track
from app.models.track_availability import TrackAvailability
from app.models.user import User
from app.models.enums import Status
from app.schemas.track_schema import TrackCreate, TrackUpdate
from app.utils.time_range import combine_date_time, interval_contains


class TracksRepository:
    """
    Repositorio para operaciones CRUD de pistas.
    Capa de acceso a datos.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, track_data: TrackCreate, company_id: int) -> Track:
        """Crear una nueva pista y persistirla en la base de datos."""
        db_track = Track(
            name=track_data.name,
            description=track_data.description,
            latitude=track_data.latitude,
            longitude=track_data.longitude,
            price_junior=track_data.price_junior,
            price_senior=track_data.price_senior,
            price_junior_half=track_data.price_junior_half,
            price_senior_half=track_data.price_senior_half,
            difficulty_level=track_data.difficulty_level.value,
            capacity=track_data.capacity,
            photos=track_data.photos or [],
            company_id=company_id,
        )
        self.db.add(db_track)
        self.db.commit()
        self.db.refresh(db_track)
        return db_track

    def get_by_id(self, track_id: int) -> Optional[Track]:
        """Obtener pista por ID."""
        return self.db.query(Track).filter(Track.id == track_id).first()

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Track]:
        """Obtener todas las pistas de una empresa, ordenadas por fecha de creación desc."""
        return (
            self.db.query(Track)
            .filter(Track.company_id == company_id)
            .order_by(Track.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, track: Track, update_data: TrackUpdate) -> Track:
        """Actualizar campos editables de una pista (partial update)."""
        if update_data.price_junior is not None:
            track.price_junior = update_data.price_junior
        if update_data.price_senior is not None:
            track.price_senior = update_data.price_senior
        if update_data.price_junior_half is not None:
            track.price_junior_half = update_data.price_junior_half
        if update_data.price_senior_half is not None:
            track.price_senior_half = update_data.price_senior_half
        if update_data.description is not None:
            track.description = update_data.description
        if update_data.latitude is not None:
            track.latitude = update_data.latitude
        if update_data.longitude is not None:
            track.longitude = update_data.longitude
        if update_data.schedule is not None:
            track.schedule = update_data.schedule
        if update_data.photos is not None:
            track.photos = update_data.photos
        self.db.commit()
        self.db.refresh(track)
        return track

    def get_tracks_for_map(self) -> List[Track]:
        """
        HU-11: Devuelve todas las pistas cuya empresa tenga status APPROVED.
        Endpoint público — no requiere usuario autenticado.
        """
        return (
            self.db.query(Track)
            .join(User, Track.company_id == User.id)
            .filter(User.status == Status.APPROVED.value)
            .all()
        )

    def get_track_with_coaches(self, track_id: int) -> Optional[Track]:
        """
        HU-17: Obtiene una pista con coaches y servicios (1 sola query con joins).
        - La pista debe pertenecer a una empresa APPROVED
        - Solo coaches APPROVED se incluyen
        """
        from app.models.coach_track import CoachTrack
        from app.models.coach import Coach
        from app.models.coach_service import CoachService

        track = (
            self.db.query(Track)
            .options(
                # Eager load relationships
                __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Track.company),
                __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Track.coach_tracks)
                .joinedload(CoachTrack.coach)
                .joinedload(Coach.user),
                __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Track.coach_tracks)
                .joinedload(CoachTrack.coach)
                .joinedload(Coach.services),
            )
            .join(User, Track.company_id == User.id)
            .filter(
                Track.id == track_id,
                User.status == Status.APPROVED.value,
            )
            .first()
        )
        return track

    # ── HU-12: Track Availability ─────────────────────────────────────────────

    def get_overlapping_availability(
        self,
        track_id: int,
        date_val: date,
        start: time,
        end: time,
        exclude_id: Optional[int] = None,
    ) -> Optional[TrackAvailability]:
        """
        Returns the first slot that overlaps [start, end) on the same track+date.
        Overlap: NEW.start < EXISTING.end AND NEW.end > EXISTING.start
        """
        q = (
            self.db.query(TrackAvailability)
            .filter(
                TrackAvailability.track_id == track_id,
                TrackAvailability.date == date_val,
                TrackAvailability.start_time < end,
                TrackAvailability.end_time > start,
            )
        )
        if exclude_id:
            q = q.filter(TrackAvailability.id != exclude_id)
        return q.first()

    def get_covering_availability(
        self,
        track_id: int,
        date_val: date,
        start: time,
        end: time,
    ) -> Optional[TrackAvailability]:
        request_start = combine_date_time(date_val, start)
        request_end = combine_date_time(date_val, end)

        slots = (
            self.db.query(TrackAvailability)
            .filter(
                TrackAvailability.track_id == track_id,
                TrackAvailability.date == date_val,
            )
            .order_by(TrackAvailability.start_time)
            .all()
        )

        for slot in slots:
            slot_start = combine_date_time(slot.date, slot.start_time)
            slot_end = combine_date_time(slot.date, slot.end_time)
            if interval_contains(slot_start, slot_end, request_start, request_end):
                return slot
        return None

    def create_availability(
        self,
        track_id: int,
        date_val: date,
        start: time,
        end: time,
        capacity: int,
        rental_type: str,
        pilot_category: str = "BOTH",
    ) -> TrackAvailability:
        slot = TrackAvailability(
            track_id=track_id,
            date=date_val,
            start_time=start,
            end_time=end,
            capacity=capacity,
            rental_type=rental_type,
            pilot_category=pilot_category,
        )
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def get_availability_by_track(self, track_id: int) -> List[TrackAvailability]:
        return (
            self.db.query(TrackAvailability)
            .filter(TrackAvailability.track_id == track_id)
            .order_by(TrackAvailability.date, TrackAvailability.start_time)
            .all()
        )

    def get_availability_by_track_and_date(self, track_id: int, date_val: date) -> List[TrackAvailability]:
        """Obtener todos los slots disponibles de una pista para una fecha específica."""
        return (
            self.db.query(TrackAvailability)
            .filter(
                TrackAvailability.track_id == track_id,
                TrackAvailability.date == date_val,
            )
            .order_by(TrackAvailability.start_time)
            .all()
        )

    def create_availability_batch(
        self,
        track_id: int,
        dates: List[date],
        start: time,
        end: time,
        capacity: int,
        rental_type: str,
        pilot_category: str = "BOTH",
    ) -> int:
        """Crea múltiples slots en una sola transacción. Retorna la cantidad creada."""
        for d in dates:
            self.db.add(
                TrackAvailability(
                    track_id=track_id,
                    date=d,
                    start_time=start,
                    end_time=end,
                    capacity=capacity,
                    rental_type=rental_type,
                    pilot_category=pilot_category,
                )
            )
        if dates:
            self.db.commit()
        return len(dates)

    def get_available_dates(self, track_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[dict]:
        """
        Obtener fechas únicas con disponibilidad de una pista.
        Retorna: [{'date': 'YYYY-MM-DD', 'slots': [{'startTime': 'HH:MM', 'endTime': 'HH:MM'}, ...]}, ...]
        """
        from datetime import datetime as dt
        
        q = self.db.query(TrackAvailability).filter(TrackAvailability.track_id == track_id)
        
        if start_date:
            q = q.filter(TrackAvailability.date >= start_date)
        if end_date:
            q = q.filter(TrackAvailability.date <= end_date)
        
        # Obtener todos los slots ordenados por fecha y hora
        slots = q.order_by(TrackAvailability.date, TrackAvailability.start_time).all()
        
        # Agrupar por fecha
        dates_dict = {}
        for slot in slots:
            date_str = str(slot.date)
            if date_str not in dates_dict:
                dates_dict[date_str] = []
            dates_dict[date_str].append({
                'startTime': slot.start_time.strftime('%H:%M'),
                'endTime': slot.end_time.strftime('%H:%M'),
            })
        
        # Convertir a lista ordenada
        result = [{'date': date_str, 'slots': times} for date_str, times in sorted(dates_dict.items())]
        return result

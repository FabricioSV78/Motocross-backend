from datetime import date, time
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.coach import Coach
from app.models.coach_track import CoachTrack
from app.models.coach_service import CoachService
from app.models.coach_availability import CoachAvailability
from app.models.track_availability import TrackAvailability
from app.models.track import Track
from app.schemas.coach_settings_schema import (
    CoachSettingsRequest,
    AvailabilityRequest,
)
from app.utils.time_range import combine_date_time, interval_contains


class CoachSettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Coach lookup ──────────────────────────────────────────────────────────

    def get_coach_by_user_id(self, user_id: int) -> Optional[Coach]:
        return self.db.query(Coach).filter(Coach.user_id == user_id).first()

    # ── Tracks ────────────────────────────────────────────────────────────────

    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        return self.db.query(Track).filter(Track.id == track_id).first()

    def replace_coach_tracks(self, coach_id: int, track_ids: List[int]) -> None:
        """Delete existing coach-track entries and insert the new ones."""
        self.db.query(CoachTrack).filter(CoachTrack.coach_id == coach_id).delete()
        for tid in track_ids:
            self.db.add(CoachTrack(coach_id=coach_id, track_id=tid))

    def get_coach_tracks(self, coach_id: int) -> List[CoachTrack]:
        return (
            self.db.query(CoachTrack)
            .filter(CoachTrack.coach_id == coach_id)
            .all()
        )

    def get_coach_track(self, coach_id: int, track_id: int) -> Optional[CoachTrack]:
        """Returns the coach-track association if it exists, else None."""
        return (
            self.db.query(CoachTrack)
            .filter(CoachTrack.coach_id == coach_id, CoachTrack.track_id == track_id)
            .first()
        )

    # ── Services ──────────────────────────────────────────────────────────────

    def replace_coach_services(self, coach_id: int, services_data: list) -> None:
        """Delete existing services and insert the new ones."""
        self.db.query(CoachService).filter(CoachService.coach_id == coach_id).delete()
        for svc in services_data:
            max_s = svc.maxStudents if svc.maxStudents is not None else 1
            self.db.add(
                CoachService(
                    coach_id=coach_id,
                    class_type=svc.classType.value,
                    mode=svc.mode.value,
                    price=svc.price,
                    max_students=max_s,
                )
            )

    def get_coach_services(self, coach_id: int) -> List[CoachService]:
        return (
            self.db.query(CoachService)
            .filter(CoachService.coach_id == coach_id)
            .all()
        )

    def get_coach_service(self, coach_id: int, class_type, mode) -> Optional[CoachService]:
        """Returns the coach service if exists, else None."""
        class_type_str = class_type.value if hasattr(class_type, 'value') else class_type
        mode_str = mode.value if hasattr(mode, 'value') else mode
        return (
            self.db.query(CoachService)
            .filter(
                CoachService.coach_id == coach_id,
                CoachService.class_type == class_type_str,
                CoachService.mode == mode_str,
            )
            .first()
        )

    # ── Availability ──────────────────────────────────────────────────────────

    def get_overlapping_availability(
        self,
        coach_id: int,
        date_val: date,
        start: time,
        end: time,
        exclude_id: Optional[int] = None,
    ) -> Optional[CoachAvailability]:
        """
        Returns the first existing slot that overlaps with [start, end) on the given date.
        Overlap condition: new.start < existing.end AND new.end > existing.start
        """
        q = (
            self.db.query(CoachAvailability)
            .filter(
                CoachAvailability.coach_id == coach_id,
                CoachAvailability.date == date_val,
                CoachAvailability.start_time < end,
                CoachAvailability.end_time > start,
            )
        )
        if exclude_id:
            q = q.filter(CoachAvailability.id != exclude_id)
        return q.first()

    def get_covering_availability(
        self,
        coach_id: int,
        date_val: date,
        start: time,
        end: time,
    ) -> Optional[CoachAvailability]:
        request_start = combine_date_time(date_val, start)
        request_end = combine_date_time(date_val, end)

        slots = (
            self.db.query(CoachAvailability)
            .filter(
                CoachAvailability.coach_id == coach_id,
                CoachAvailability.date == date_val,
            )
            .order_by(CoachAvailability.start_time)
            .all()
        )

        for slot in slots:
            slot_start = combine_date_time(slot.date, slot.start_time)
            slot_end = combine_date_time(slot.date, slot.end_time)
            if interval_contains(slot_start, slot_end, request_start, request_end):
                return slot
        return None

    def get_covering_track_availability(
        self,
        track_id: int,
        date_val: date,
        start: time,
        end: time,
    ) -> Optional[TrackAvailability]:
        """Return the track slot that fully contains the coach window, if any."""
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
        self, coach_id: int, req: AvailabilityRequest
    ) -> CoachAvailability:
        start = time.fromisoformat(req.startTime)
        end = time.fromisoformat(req.endTime)
        class_type_str = req.classType.value if hasattr(req.classType, 'value') else req.classType
        mode_str = req.mode.value if hasattr(req.mode, 'value') else req.mode
        slot = CoachAvailability(
            coach_id=coach_id,
            track_id=req.trackId,
            date=req.date,
            start_time=start,
            end_time=end,
            class_type=class_type_str,
            mode=mode_str,
        )
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def get_availability_by_coach(self, coach_id: int, from_date: Optional[date] = None) -> List[CoachAvailability]:
        q = (
            self.db.query(CoachAvailability)
            .filter(CoachAvailability.coach_id == coach_id)
        )
        if from_date is not None:
            q = q.filter(CoachAvailability.date >= from_date)
        return q.order_by(CoachAvailability.date, CoachAvailability.start_time).all()

    def get_availability_by_coach_and_track(self, coach_id: int, track_id: int) -> List[CoachAvailability]:
        """Obtener todos los slots del coach para una pista específica."""
        return (
            self.db.query(CoachAvailability)
            .filter(
                CoachAvailability.coach_id == coach_id,
                CoachAvailability.track_id == track_id,
            )
            .order_by(CoachAvailability.date, CoachAvailability.start_time)
            .all()
        )

    def get_availability_by_coach_track_and_date(self, coach_id: int, track_id: int, date_val: date) -> List[CoachAvailability]:
        """Obtener los slots del coach para una pista y fecha específica."""
        return (
            self.db.query(CoachAvailability)
            .filter(
                CoachAvailability.coach_id == coach_id,
                CoachAvailability.track_id == track_id,
                CoachAvailability.date == date_val,
            )
            .order_by(CoachAvailability.start_time)
            .all()
        )

    def create_availability_bulk(
        self,
        coach_id: int,
        track_id: int,
        dates: List[date],
        start: time,
        end: time,
        class_type=None,
        mode=None,
    ) -> None:
        """Agrega múltiples slots a la sesión sin commit (el caller hace commit)."""
        class_type_str = class_type.value if hasattr(class_type, 'value') else class_type
        mode_str = mode.value if hasattr(mode, 'value') else mode
        for d in dates:
            self.db.add(
                CoachAvailability(
                    coach_id=coach_id,
                    track_id=track_id,
                    date=d,
                    start_time=start,
                    end_time=end,
                    class_type=class_type_str,
                    mode=mode_str,
                )
            )

    def get_available_dates_for_coach_track(self, coach_id: int, track_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[dict]:
        """
        Obtener fechas únicas con disponibilidad de un coach en una pista específica.
        Retorna: [{'date': 'YYYY-MM-DD', 'slots': [{'startTime': 'HH:MM', 'endTime': 'HH:MM', 'classType': 'HOURLY', 'mode': 'ONE_TO_ONE'}, ...]}, ...]
        """
        q = self.db.query(CoachAvailability).filter(
            CoachAvailability.coach_id == coach_id,
            CoachAvailability.track_id == track_id,
        )
        
        if start_date:
            q = q.filter(CoachAvailability.date >= start_date)
        if end_date:
            q = q.filter(CoachAvailability.date <= end_date)
        
        # Obtener todos los slots ordenados por fecha y hora
        slots = q.order_by(CoachAvailability.date, CoachAvailability.start_time).all()
        
        # Agrupar por fecha
        dates_dict = {}
        for slot in slots:
            date_str = str(slot.date)
            if date_str not in dates_dict:
                dates_dict[date_str] = []
            dates_dict[date_str].append({
                'startTime': slot.start_time.strftime('%H:%M'),
                'endTime': slot.end_time.strftime('%H:%M'),
                'classType': slot.class_type,
                'mode': slot.mode,
            })
        
        # Convertir a lista ordenada
        result = [{'date': date_str, 'slots': times} for date_str, times in sorted(dates_dict.items())]
        return result

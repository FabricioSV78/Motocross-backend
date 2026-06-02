from fastapi import HTTPException, status

from app.repositories.coach_settings_repository import CoachSettingsRepository
from app.schemas.coach_settings_schema import (
    CoachSettingsRequest,
    CoachSettingsResponse,
    CoachSettingsGetResponse,
    ServiceItemResponse,
    TrackRefResponse,
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilityItem,
    AvailabilityBatchRequest,
    AvailabilityBatchResponse,
)


class CoachSettingsService:
    def __init__(self, repo: CoachSettingsRepository):
        self.repo = repo

    @staticmethod
    def _track_slot_accepts_service(track_slot, class_type) -> bool:
        class_type_value = class_type.value if hasattr(class_type, "value") else class_type
        if class_type_value == "FULL_DAY":
            return track_slot.rental_type == "FULL_DAY"
        return track_slot.rental_type in {"HALF_DAY", "FULL_DAY"}

    def _get_coach_or_404(self, user_id: int):
        coach = self.repo.get_coach_by_user_id(user_id)
        if not coach:
            raise HTTPException(status_code=404, detail="Coach profile not found")
        return coach

    # ── HU-10: Settings ───────────────────────────────────────────────────────

    def update_settings(
        self, user_id: int, req: CoachSettingsRequest
    ) -> CoachSettingsResponse:
        coach = self._get_coach_or_404(user_id)

        # Validate that every track exists
        for t in req.tracks:
            if not self.repo.get_track_by_id(t.trackId):
                raise HTTPException(
                    status_code=404,
                    detail=f"Track with id {t.trackId} not found",
                )

        # Validate no duplicate (classType, mode) combos in the payload
        seen_services: set = set()
        for s in req.services:
            key = (s.classType, s.mode)
            if key in seen_services:
                raise HTTPException(
                    status_code=422,
                    detail=f"Servicio duplicado: {s.classType.value}/{s.mode.value}. Cada combinación de tipo y modalidad debe ser única.",
                )
            seen_services.add(key)

        self.repo.replace_coach_tracks(
            coach.id, [t.trackId for t in req.tracks]
        )
        self.repo.replace_coach_services(coach.id, req.services)
        self.repo.db.commit()

        return CoachSettingsResponse(message="Settings updated successfully")

    def get_settings(self, user_id: int) -> CoachSettingsGetResponse:
        coach = self._get_coach_or_404(user_id)

        coach_tracks = self.repo.get_coach_tracks(coach.id)
        coach_services = self.repo.get_coach_services(coach.id)

        tracks_out = [
            TrackRefResponse(
                trackId=ct.track_id,
                trackName=ct.track.name if ct.track else "",
            )
            for ct in coach_tracks
        ]

        services_out = [
            ServiceItemResponse(
                id=svc.id,
                classType=svc.class_type,
                mode=svc.mode,
                price=svc.price,
                maxStudents=svc.max_students,
            )
            for svc in coach_services
        ]

        return CoachSettingsGetResponse(tracks=tracks_out, services=services_out)

    # ── HU-13: Availability ───────────────────────────────────────────────────

    def create_availability(
        self, user_id: int, req: AvailabilityRequest
    ) -> AvailabilityResponse:
        from datetime import time

        coach = self._get_coach_or_404(user_id)

        # Validate track exists
        track = self.repo.get_track_by_id(req.trackId)
        if not track:
            raise HTTPException(
                status_code=404,
                detail=f"Track with id {req.trackId} not found",
            )

        # Validate the coach has this track configured in their settings
        if not self.repo.get_coach_track(coach.id, req.trackId):
            raise HTTPException(
                status_code=400,
                detail="You can only add availability for tracks configured in your profile. Go to Settings and add the track first.",
            )

        # Validate the coach has this service (classType, mode) configured
        service = self.repo.get_coach_service(coach.id, req.classType, req.mode)
        if not service:
            raise HTTPException(
                status_code=400,
                detail=f"You have not configured the service {req.classType.value}/{req.mode.value}. Go to Settings and add it first.",
            )

        start = time.fromisoformat(req.startTime)
        end = time.fromisoformat(req.endTime)

        track_slot = self.repo.get_covering_track_availability(
            req.trackId, req.date, start, end
        )
        if not track_slot:
            raise HTTPException(
                status_code=400,
                detail="This coach time must fit inside a published availability window for the selected track. Choose one of the track's available time slots first.",
            )
        if not self._track_slot_accepts_service(track_slot, req.classType):
            raise HTTPException(
                status_code=400,
                detail="This service type is not compatible with the selected track availability window.",
            )

        # Overlap check
        overlap = self.repo.get_overlapping_availability(
            coach.id, req.date, start, end
        )
        if overlap:
            raise HTTPException(
                status_code=409,
                detail="This time slot overlaps with an existing availability entry",
            )

        self.repo.create_availability(coach.id, req)
        return AvailabilityResponse(message="Availability slot created successfully")

    def get_availability(self, user_id: int, from_date=None) -> list[AvailabilityItem]:
        from datetime import date as date_type
        coach = self._get_coach_or_404(user_id)
        effective_from = from_date if from_date is not None else date_type.today()
        slots = self.repo.get_availability_by_coach(coach.id, from_date=effective_from)

        return [
            AvailabilityItem(
                id=s.id,
                trackId=s.track_id,
                trackName=s.track.name if s.track else "",
                date=s.date,
                startTime=s.start_time.strftime("%H:%M"),
                endTime=s.end_time.strftime("%H:%M"),
                classType=s.class_type,
                mode=s.mode,
                maxStudents=self.repo.get_coach_service(coach.id, s.class_type, s.mode).max_students if self.repo.get_coach_service(coach.id, s.class_type, s.mode) else 1,
            )
            for s in slots
        ]

    def create_availability_batch(
        self, user_id: int, req: AvailabilityBatchRequest
    ) -> AvailabilityBatchResponse:
        from datetime import time as time_type

        coach = self._get_coach_or_404(user_id)

        track = self.repo.get_track_by_id(req.trackId)
        if not track:
            raise HTTPException(
                status_code=404,
                detail=f"Track with id {req.trackId} not found",
            )

        if not self.repo.get_coach_track(coach.id, req.trackId):
            raise HTTPException(
                status_code=400,
                detail="You can only add availability for tracks configured in your profile. Go to Settings and add the track first.",
            )

        # Validate the coach has this service (classType, mode) configured
        service = self.repo.get_coach_service(coach.id, req.classType, req.mode)
        if not service:
            raise HTTPException(
                status_code=400,
                detail=f"You have not configured the service {req.classType.value}/{req.mode.value}. Go to Settings and add it first.",
            )

        start = time_type.fromisoformat(req.startTime)
        end = time_type.fromisoformat(req.endTime)

        to_create = []
        skipped_overlap = 0
        skipped_track = 0
        for d in req.dates:
            track_slot = self.repo.get_covering_track_availability(
                req.trackId, d, start, end
            )
            if not track_slot or not self._track_slot_accepts_service(track_slot, req.classType):
                skipped_track += 1
                continue
            overlap = self.repo.get_overlapping_availability(coach.id, d, start, end)
            if overlap:
                skipped_overlap += 1
            else:
                to_create.append(d)

        if to_create:
            self.repo.create_availability_bulk(coach.id, req.trackId, to_create, start, end, req.classType, req.mode)
            self.repo.db.commit()

        created = len(to_create)
        skipped = skipped_overlap + skipped_track
        return AvailabilityBatchResponse(
            created=created,
            skipped=skipped,
            message=(
                f"{created} slot(s) created, {skipped} skipped "
                f"({skipped_overlap} coach overlap, {skipped_track} without matching track availability)."
            ),
        )

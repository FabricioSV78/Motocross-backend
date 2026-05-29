from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.coach import Coach
from app.models.enums import Status


class CoachRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[Coach]:
        return self.db.query(Coach).filter(Coach.user_id == user_id).first()

    def get_by_id(self, coach_id: int) -> Optional[Coach]:
        return self.db.query(Coach).filter(Coach.id == coach_id).first()

    def create(self, user_id: int, experience: Optional[str] = None) -> Coach:
        coach = Coach(
            user_id=user_id,
            experience=experience,
            status=Status.PENDING.value,
        )
        self.db.add(coach)
        self.db.commit()
        self.db.refresh(coach)
        return coach

    def update_certificate(self, user_id: int, certificate_url: str) -> Optional[Coach]:
        coach = self.get_by_user_id(user_id)
        if not coach:
            return None
        coach.certificate_url = certificate_url
        coach.status = Status.PENDING.value
        self.db.commit()
        self.db.refresh(coach)
        return coach

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Coach]:
        """Obtener todos los coaches"""
        return self.db.query(Coach).offset(skip).limit(limit).all()

    def get_by_status(self, status: Status, skip: int = 0, limit: int = 100) -> List[Coach]:
        """Obtener coaches filtrados por status"""
        return (
            self.db.query(Coach)
            .filter(Coach.status == status.value)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, coach_id: int, new_status: Status) -> Optional[Coach]:
        coach = self.get_by_id(coach_id)
        if not coach:
            return None
        coach.status = new_status.value
        self.db.commit()
        self.db.refresh(coach)
        return coach

    def update_status_by_user_id(self, user_id: int, new_status: Status) -> Optional[Coach]:
        """Cambiar status del coach buscando por user_id (útil para verify-provider).
        
        También sincroniza users.status para que el login y el token reflejen
        el estado de aprobación correcto.
        """
        coach = self.get_by_user_id(user_id)
        if not coach:
            return None
        coach.status = new_status.value
        # Sincronizar el estado en la tabla users para que login y JWT
        # reflejen si el coach está APPROVED o REJECTED
        if coach.user:
            coach.user.status = new_status.value
        self.db.commit()
        self.db.refresh(coach)
        return coach

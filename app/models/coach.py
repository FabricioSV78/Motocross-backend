from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import Status


class Coach(Base):
    """
    Modelo de Coach
    Representa a los entrenadores de motocross del sistema.
    
    Relación 1-1 con User (role = COACH).
    El coach debe subir un certificado y esperar aprobación del admin.
    """
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    certificate_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default=Status.PENDING.value)
    foto = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación 1-1 con User
    user = relationship("User", back_populates="coach")

    # HU-10: pistas y servicios del coach
    coach_tracks = relationship("CoachTrack", back_populates="coach", cascade="all, delete-orphan")
    services = relationship("CoachService", back_populates="coach", cascade="all, delete-orphan")

    # HU-13: disponibilidad del coach
    availability = relationship("CoachAvailability", back_populates="coach", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coach user_id={self.user_id} status={self.status}>"

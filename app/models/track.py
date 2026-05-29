from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import DifficultyLevel


class Track(Base):
    """
    Modelo de Pista de Motocross.
    Cada pista pertenece a una empresa (relación Track → User con rol COMPANY).
    """
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    price_junior = Column(Float, nullable=False)
    price_senior = Column(Float, nullable=False)
    price_junior_half = Column(Float, nullable=True)   # precio medio día junior (opcional)
    price_senior_half = Column(Float, nullable=True)   # precio medio día senior (opcional)
    difficulty_level = Column(String, nullable=False, default=DifficultyLevel.BEGINNER.value)
    capacity = Column(Integer, nullable=False)
    photos = Column(JSON, nullable=True, default=list)    # lista de URLs
    schedule = Column(JSON, nullable=True, default=list)   # lista de horarios, ej: ["08:00-10:00"]
    company_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación: la empresa propietaria
    company = relationship("User", foreign_keys=[company_id])

    # HU-12: disponibilidad/horarios de la pista
    availability = relationship("TrackAvailability", back_populates="track", cascade="all, delete-orphan")

    # HU-17: coaches que enseñan en esta pista (N-N via coach_tracks)
    coach_tracks = relationship("CoachTrack", back_populates="track", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Track id={self.id} name={self.name!r} company_id={self.company_id}>"

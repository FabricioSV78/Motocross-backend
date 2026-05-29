from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import PilotLevel


class PilotProfile(Base):
    """
    Modelo de Perfil de Piloto
    Información adicional específica para usuarios con rol PILOT
    Relación 1-1 con User
    """
    __tablename__ = "pilot_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Información del perfil
    foto = Column(String, nullable=True)        # URL foto de perfil del piloto
    foto_moto = Column(String, nullable=True)   # URL foto de la moto
    nivel = Column(String, nullable=False, default=PilotLevel.BEGINNER.value)
    moto = Column(String, nullable=True)
    
    # Relación con User
    user = relationship("User", back_populates="pilot_profile", uselist=False)

    def __repr__(self):
        return f"<PilotProfile user_id={self.user_id} nivel={self.nivel}>"

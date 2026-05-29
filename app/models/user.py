from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import Role, Status


class User(Base):
    """
    Modelo de Usuario
    Representa a los pilotos, empresas y administradores del sistema
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default=Role.PILOT.value)
    status = Column(String, nullable=False, default=Status.ACTIVE.value)
    
    # Campos específicos para empresas
    nombre_empresa = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con PilotProfile (1-1)
    pilot_profile = relationship("PilotProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relación con Coach (1-1)
    coach = relationship("Coach", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import ClassType, ClassMode


class CoachService(Base):
    """
    HU-10: Servicios/precios que ofrece un coach.
    Combina class_type × mode con precio y capacidad.
    """
    __tablename__ = "coach_services"
    __table_args__ = (
        UniqueConstraint("coach_id", "class_type", "mode", name="uq_coach_service"),
    )

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False)
    class_type = Column(String, nullable=False)   # HOURLY | HALF_DAY | FULL_DAY
    mode = Column(String, nullable=False)          # ONE_TO_ONE | GROUP
    price = Column(Float, nullable=False)
    max_students = Column(Integer, nullable=False, default=1)

    coach = relationship("Coach", back_populates="services")

    def __repr__(self):
        return f"<CoachService coach_id={self.coach_id} {self.class_type}/{self.mode} price={self.price}>"

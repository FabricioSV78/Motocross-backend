from sqlalchemy import Column, Integer, Date, Time, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class CoachAvailability(Base):
    """
    HU-13: Disponibilidad horaria del coach.
    Un coach define en qué pista, en qué franja horaria puede enseñar,
    qué tipo de servicio (HOURLY, HALF_DAY, FULL_DAY) y modalidad (ONE_TO_ONE, GROUP).
    """
    __tablename__ = "coach_availability"
    __table_args__ = (
        Index("ix_coach_avail_coach_date", "coach_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    class_type = Column(String, nullable=False)  # HOURLY | HALF_DAY | FULL_DAY
    mode = Column(String, nullable=False)         # ONE_TO_ONE | GROUP

    coach = relationship("Coach", back_populates="availability")
    track = relationship("Track")

    def __repr__(self):
        return (
            f"<CoachAvailability coach_id={self.coach_id} track_id={self.track_id} "
            f"date={self.date} {self.start_time}-{self.end_time} "
            f"{self.class_type}/{self.mode}>"
        )

from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class TrackAvailability(Base):
    """
    HU-12: Disponibilidad horaria de una pista.
    Una empresa define franjas horarias con capacidad y precios por tipo de piloto.
    """
    __tablename__ = "track_availability"
    __table_args__ = (
        Index("ix_track_avail_track_date", "track_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    capacity = Column(Integer, nullable=False)
    rental_type = Column(String, nullable=False)   # HALF_DAY | FULL_DAY
    pilot_category = Column(String, nullable=False, server_default="BOTH")  # JUNIOR | SENIOR | BOTH

    track = relationship("Track", back_populates="availability")

    def __repr__(self):
        return (
            f"<TrackAvailability track_id={self.track_id} "
            f"date={self.date} {self.start_time}-{self.end_time}>"
        )

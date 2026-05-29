from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class CoachTrack(Base):
    """
    HU-10: Pistas donde un coach puede enseñar.
    Relación N-N entre coaches y tracks.
    """
    __tablename__ = "coach_tracks"
    __table_args__ = (UniqueConstraint("coach_id", "track_id", name="uq_coach_track"),)

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)

    coach = relationship("Coach", back_populates="coach_tracks")
    track = relationship("Track")

    def __repr__(self):
        return f"<CoachTrack coach_id={self.coach_id} track_id={self.track_id}>"

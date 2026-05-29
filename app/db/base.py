"""
Importar todos los modelos aquí para que Alembic los detecte
"""
from app.db.session import Base
from app.models.user import User
from app.models.pilot_profile import PilotProfile
from app.models.track import Track  # noqa: F401
from app.models.coach import Coach  # noqa: F401
from app.models.coach_track import CoachTrack  # noqa: F401
from app.models.coach_service import CoachService  # noqa: F401
from app.models.coach_availability import CoachAvailability  # noqa: F401
from app.models.track_availability import TrackAvailability  # noqa: F401

# Exportar Base para usar en alembic
__all__ = ["Base"]

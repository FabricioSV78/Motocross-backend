import enum


class Role(str, enum.Enum):
    """
    Roles de usuario en el sistema
    """
    PILOT = "PILOT"
    COMPANY = "COMPANY"
    COACH = "COACH"
    ADMIN = "ADMIN"


class Status(str, enum.Enum):
    """
    Estados de usuario en el sistema
    """
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class PilotLevel(str, enum.Enum):
    """
    Niveles de experiencia de piloto
    """
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    PRO = "PRO"


class DifficultyLevel(str, enum.Enum):
    """
    Niveles de dificultad de una pista
    """
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class ClassType(str, enum.Enum):
    HOURLY = "HOURLY"
    HALF_DAY = "HALF_DAY"
    FULL_DAY = "FULL_DAY"


class ClassMode(str, enum.Enum):
    ONE_TO_ONE = "ONE_TO_ONE"
    GROUP = "GROUP"


class RentalType(str, enum.Enum):
    HALF_DAY = "HALF_DAY"
    FULL_DAY = "FULL_DAY"


class PilotCategory(str, enum.Enum):
    JUNIOR = "JUNIOR"
    SENIOR = "SENIOR"
    BOTH = "BOTH"


class ReservationStatus(str, enum.Enum):
    """
    Estados de una reserva
    """
    PENDING_PAYMENT = "PENDING_PAYMENT"  # Esperando confirmación de pago
    CONFIRMED = "CONFIRMED"               # Pago confirmado y reserva válida
    CANCELLED = "CANCELLED"               # Cancelada (pago fallido o cancelada por usuario)
    COMPLETED = "COMPLETED"               # Completada (la lección ya ocurrió)


class PaymentStatus(str, enum.Enum):
    """
    Estados de un pago
    """
    PENDING = "PENDING"         # En espera de confirmación
    SUCCESS = "SUCCESS"         # Pago exitoso
    FAILED = "FAILED"           # Pago fallido

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configuración específica para SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Railway PostgreSQL normalmente requiere TLS; si la URL no lo trae explícito,
# lo añadimos para evitar errores de arranque por conexión insegura.
database_url = settings.DATABASE_URL
if database_url.startswith(("postgresql://", "postgres://")) and "sslmode=" not in database_url:
    if ".proxy.rlwy.net" in database_url or "railway.app" in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

# Crear engine de SQLAlchemy
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Crear SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de base de datos
    Se usa en FastAPI con Depends()
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

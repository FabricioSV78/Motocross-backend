from typing import Any
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando variables de entorno
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Motocross Booking Platform"
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: str = '["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]'
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""  # sk_test_... o sk_live_...
    STRIPE_WEBHOOK_SECRET: str = ""  # whsec_...
    
    # Cloudflare R2 / S3 compatible uploads
    R2_ENABLED: bool = False
    R2_ENDPOINT_URL: str = ""  # e.g. https://<account_id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""
    R2_REGION: str = "auto"
    R2_PUBLIC_URL: str = ""  # Optional public base URL (e.g. https://cdn.example.com)
    
    # Default currency
    DEFAULT_CURRENCY: str = "AUD"
    
    @property
    def cors_origins(self) -> list[str]:
        """Parsear CORS origins desde string JSON"""
        return json.loads(self.BACKEND_CORS_ORIGINS)


# Instancia global de configuración
settings = Settings()

# Directorio absoluto de uploads — resuelto desde la ubicación de este archivo
# config.py está en  motocross-backend/app/core/config.py
# .parent                 → motocross-backend/app/core/
# .parent.parent          → motocross-backend/app/
# .parent.parent.parent   → motocross-backend/
UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"

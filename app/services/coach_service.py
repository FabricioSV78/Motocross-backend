import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.repositories.coach_repository import CoachRepository
from app.core.config import UPLOAD_DIR, settings
from app.services.storage_service import storage_service


CERTIFICATES_DIR: Path = UPLOAD_DIR / "certificates"
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class CoachService:
    def __init__(self, db: Session):
        self.db = db
        self.coach_repo = CoachRepository(db)

    async def upload_certificate(self, user_id: int, file: UploadFile) -> str:
        """
        HU-09: Subir certificado del coach.

        Valida el tipo y tamaño del archivo, lo guarda en disco y actualiza
        certificate_url + status en la tabla coaches.

        Returns:
            Mensaje de confirmación.
        """
        # Validar tipo de archivo
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format. Only PDF, JPG, PNG, or WebP.",
            )

        # Leer contenido y validar tamaño
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size must be under 5 MB.",
            )

        # Determinar extensión
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "application/pdf": "pdf",
        }
        ext = ext_map.get(file.content_type, "bin")
        filename = f"certificate_{user_id}_{uuid.uuid4().hex[:10]}.{ext}"

        # Verificar que existe el registro de coach
        coach = self.coach_repo.get_by_user_id(user_id)
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coach profile not found.",
            )

        # Eliminar certificado anterior (R2 o local)
        if coach.certificate_url:
            # Si R2 está activado, intentamos eliminar por key
            try:
                key = storage_service.key_from_url(coach.certificate_url)
                if key:
                    storage_service.delete(key)
                else:
                    # Fallback local file removal for previous local path
                    old_filename = coach.certificate_url.rsplit("/", 1)[-1]
                    old_path = CERTIFICATES_DIR / old_filename
                    if old_path.is_file():
                        old_path.unlink()
            except Exception:
                # Fallback: try local delete
                old_filename = coach.certificate_url.rsplit("/", 1)[-1]
                old_path = CERTIFICATES_DIR / old_filename
                if old_path.is_file():
                    old_path.unlink()

        # Guardar nuevo archivo: subir a R2 si está disponible, si no, guardar localmente
        if storage_service.enabled:
            key = f"certificates/{filename}"
            public_url = storage_service.upload_bytes(key, contents, content_type=file.content_type)
            self.coach_repo.update_certificate(user_id, public_url)
        else:
            CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)
            with open(CERTIFICATES_DIR / filename, "wb") as fp:
                fp.write(contents)
            relative_url = f"/uploads/certificates/{filename}"
            self.coach_repo.update_certificate(user_id, relative_url)

        return "Certificate uploaded successfully"

from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
import uuid
from sqlalchemy.orm import Session
from app.core.config import UPLOAD_DIR
from app.services.storage_service import storage_service
from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate, UserProfileResponse, UpdateUserProfileRequest, UploadPhotoResponse
from app.services.user import UserService
from app.api.deps import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.pilot_profile import PilotProfile
from app.models.enums import Role, PilotLevel


router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener información básica del usuario actual
    
    Requiere autenticación (token JWT)
    
    Para pilotos, usar /users/me/profile para obtener información completa del perfil
    """
    return current_user


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    HU-05: Ver perfil completo de piloto
    
    Obtener perfil completo del usuario piloto incluyendo:
    - Datos básicos (id, email, nombre)
    - Foto de perfil
    - Nivel de experiencia (BEGINNER, INTERMEDIATE, PRO)
    - Información de la moto
    
    Requiere autenticación (token JWT)
    Solo disponible para usuarios con rol PILOT
    
    Returns:
        Perfil completo del piloto
        
    Raises:
        403: Si el usuario no es piloto
        404: Si el usuario no existe
    """
    user_service = UserService(db)
    return user_service.get_my_profile(current_user.id)


@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(
    profile_data: UpdateUserProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    HU-06: Editar perfil del piloto autenticado
    """
    user_service = UserService(db)
    return user_service.update_my_profile(current_user.id, profile_data)


@router.post("/me/upload-photo", response_model=UploadPhotoResponse)
async def upload_photo(
    tipo: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Subir foto de perfil o de moto del piloto autenticado.
    tipo: 'avatar' | 'moto'
    - Elimina el archivo anterior del disco (evita archivos huérfanos).
    - Guarda la ruta relativa en BD (no la URL absoluta), para que no quede
      atado a un host específico y funcione en cualquier entorno.
    """
    if tipo not in ("avatar", "moto"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'avatar' o 'moto'")

    ALLOWED = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Formato no permitido. Solo JPG, PNG o WebP.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen no puede superar 5 MB.")

    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{tipo}_{current_user.id}_{uuid.uuid4().hex[:10]}.{ext}"

    # Cargar o crear el perfil de piloto
    pilot_profile = db.query(PilotProfile).filter(PilotProfile.user_id == current_user.id).first()
    if not pilot_profile:
        pilot_profile = PilotProfile(user_id=current_user.id, nivel=PilotLevel.BEGINNER.value)
        db.add(pilot_profile)
        db.flush()  # obtener ID sin commit todavía

    # Eliminar el archivo anterior del disco para no acumular huérfanos
    old_path: str | None = pilot_profile.foto if tipo == "avatar" else pilot_profile.foto_moto
    if old_path:
        # Intentar eliminar en R2 si está configurado
        try:
            key = storage_service.key_from_url(old_path)
            if key and storage_service.enabled:
                storage_service.delete(key)
            else:
                old_filename = old_path.rsplit("/", 1)[-1]  # funciona con '/uploads/x.jpg' o 'http://.../x.jpg'
                old_file = UPLOAD_DIR / old_filename
                if old_file.is_file():
                    old_file.unlink()
        except Exception:
            old_filename = old_path.rsplit("/", 1)[-1]
            old_file = UPLOAD_DIR / old_filename
            if old_file.is_file():
                old_file.unlink()

    # Guardar nuevo archivo: subir a R2 si está habilitado, sino guardar local
    if storage_service.enabled:
        key = f"users/{tipo}/{filename}"
        public_url = storage_service.upload_bytes(key, contents, content_type=file.content_type)
        if tipo == "avatar":
            pilot_profile.foto = public_url
        else:
            pilot_profile.foto_moto = public_url
        db.commit()
        return UploadPhotoResponse(url=public_url)
    else:
        # Guardar localmente
        UPLOAD_DIR.mkdir(exist_ok=True)
        with open(UPLOAD_DIR / filename, "wb") as fp:
            fp.write(contents)

        # Persistir la ruta RELATIVA en BD (no la URL absoluta)
        relative_url = f"/uploads/{filename}"
        if tipo == "avatar":
            pilot_profile.foto = relative_url
        else:
            pilot_profile.foto_moto = relative_url
        db.commit()

        return UploadPhotoResponse(url=relative_url)


@router.get("/", response_model=list[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Obtener lista de usuarios
    
    Solo para administradores
    """
    user_service = UserService(db)
    return user_service.get_users(skip, limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Obtener usuario por ID
    
    Solo para administradores
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Eliminar usuario
    
    Solo para administradores
    """
    user_service = UserService(db)
    user_service.delete_user(user_id)
    return None

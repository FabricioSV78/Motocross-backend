from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.enums import Status, Role
from app.repositories.user import UserRepository
from app.schemas.user import TokenPayload


# OAuth2 scheme para obtener el token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login-oauth")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependencia para obtener el usuario actual desde el JWT token
    
    Args:
        db: Sesión de base de datos
        token: JWT token del header Authorization
        
    Returns:
        Usuario actual
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=int(user_id))
    except JWTError:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(token_data.sub)
    
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia para verificar que el usuario actual está activo
    
    Args:
        current_user: Usuario actual
        
    Returns:
        Usuario actual si está activo
        
    Raises:
        HTTPException: Si el usuario está inactivo
    """
    ALLOWED_STATUSES = {Status.ACTIVE, Status.APPROVED}
    if current_user.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive or pending approval"
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia para verificar que el usuario actual es administrador
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have sufficient permissions"
        )
    return current_user


def get_current_coach(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia para verificar que el usuario actual es un coach.

    A diferencia de get_current_active_user, permite status PENDING para que
    el coach pueda subir su certificado antes de ser aprobado.
    """
    if current_user.role != Role.COACH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can perform this action",
        )
    return current_user


def get_current_company(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia para verificar que el usuario actual es una empresa (COMPANY).
    Requiere status APPROVED para poder operar.
    """
    if current_user.role != Role.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only companies can perform this action",
        )
    if current_user.status != Status.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company is not approved yet",
        )
    return current_user

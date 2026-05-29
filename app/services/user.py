from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.enums import Role
from app.schemas.user import UserProfileResponse, PilotProfileCreate, UpdateUserProfileRequest
from app.repositories.user import UserRepository


class UserService:
    """
    Servicio de usuarios
    Lógica de negocio para operaciones con usuarios
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        return self.user_repo.get_by_id(user_id)
    
    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Obtener lista de usuarios"""
        return self.user_repo.get_all(skip, limit)
    
    def delete_user(self, user_id: int) -> bool:
        """
        Eliminar usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si se eliminó
            
        Raises:
            HTTPException: Si el usuario no existe
        """
        deleted = self.user_repo.delete(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return True
    
    def get_my_profile(self, user_id: int) -> UserProfileResponse:
        """
        Obtener perfil completo del usuario piloto
        HU-05: Ver perfil
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Perfil completo del usuario con información de piloto
            
        Raises:
            HTTPException: Si el usuario no existe, no es piloto o no tiene perfil
        """
        # Obtener usuario con perfil
        user = self.user_repo.get_user_with_profile(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verificar que sea piloto
        if user.role != Role.PILOT.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders can view their profile"
            )
        
        # Si no tiene perfil, crear uno por defecto
        if not user.pilot_profile:
            profile_data = PilotProfileCreate()
            self.user_repo.create_pilot_profile(user_id, profile_data)
            # Refrescar usuario para obtener el perfil
            user = self.user_repo.get_user_with_profile(user_id)
        
        # Construir respuesta
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            nombre=user.nombre,
            foto=user.pilot_profile.foto,
            foto_moto=user.pilot_profile.foto_moto,
            nivel=user.pilot_profile.nivel,
            moto=user.pilot_profile.moto
        )

    def update_my_profile(
        self, user_id: int, profile_data: UpdateUserProfileRequest
    ) -> UserProfileResponse:
        """
        Actualizar perfil del piloto autenticado
        HU-06: Editar perfil

        Args:
            user_id: ID del usuario
            profile_data: Datos a actualizar (nombre, foto, nivel, moto)

        Returns:
            Perfil actualizado

        Raises:
            HTTPException 404: Si el usuario no existe
            HTTPException 403: Si el usuario no es piloto
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.role != Role.PILOT.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders can edit their profile",
            )

        updated_user = self.user_repo.update_user_profile(user_id, profile_data)

        pilot_profile = updated_user.pilot_profile
        return UserProfileResponse(
            id=updated_user.id,
            email=updated_user.email,
            nombre=updated_user.nombre,
            foto=pilot_profile.foto if pilot_profile else None,
            foto_moto=pilot_profile.foto_moto if pilot_profile else None,
            nivel=pilot_profile.nivel if pilot_profile else "BEGINNER",
            moto=pilot_profile.moto if pilot_profile else None,
        )

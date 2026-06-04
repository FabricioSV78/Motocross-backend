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
        Obtener perfil completo del usuario (piloto o coach)
        HU-05 / HU-09: Ver perfil
        """
        # Obtener usuario con perfil
        user = self.user_repo.get_user_with_profile(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Permitir tanto pilotos como coaches
        if user.role not in (Role.PILOT.value, Role.COACH.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders and coaches can view their profile"
            )
        
        if user.role == Role.PILOT.value:
            # Si no tiene perfil de piloto, crear uno por defecto
            if not user.pilot_profile:
                profile_data = PilotProfileCreate()
                self.user_repo.create_pilot_profile(user_id, profile_data)
                # Refrescar usuario para obtener el perfil
                user = self.user_repo.get_user_with_profile(user_id)
            
            return UserProfileResponse(
                id=user.id,
                email=user.email,
                nombre=user.nombre,
                foto=user.pilot_profile.foto,
                foto_moto=user.pilot_profile.foto_moto,
                nivel=user.pilot_profile.nivel,
                moto=user.pilot_profile.moto,
                role=user.role,
                status=user.status
            )
        else:
            # Es un coach
            from app.repositories.coach_repository import CoachRepository
            coach_repo = CoachRepository(self.db)
            coach = coach_repo.get_by_user_id(user_id)
            if not coach:
                # Si no existe, crearlo
                coach = coach_repo.create(user_id=user_id)
            
            return UserProfileResponse(
                id=user.id,
                email=user.email,
                nombre=user.nombre,
                foto=coach.foto,
                foto_moto=None,
                nivel=None,
                moto=None,
                role=user.role,
                status=coach.status,
                telefono=user.telefono,
                bio=coach.bio,
                experience=coach.experience,
                certificate_url=coach.certificate_url
            )

    def update_my_profile(
        self, user_id: int, profile_data: UpdateUserProfileRequest
    ) -> UserProfileResponse:
        """
        Actualizar perfil del usuario autenticado (piloto o coach)
        HU-06 / CRUD coach
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.role not in (Role.PILOT.value, Role.COACH.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders and coaches can edit their profile",
            )

        if user.role == Role.PILOT.value:
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
                role=updated_user.role,
                status=updated_user.status
            )
        else:
            # Es un coach
            # Actualizar nombre y teléfono en User
            user.nombre = profile_data.nombre
            if profile_data.telefono is not None:
                user.telefono = profile_data.telefono
            
            # Obtener y actualizar coach
            from app.repositories.coach_repository import CoachRepository
            coach_repo = CoachRepository(self.db)
            coach = coach_repo.get_by_user_id(user_id)
            if not coach:
                coach = coach_repo.create(user_id=user_id)
            
            if profile_data.foto is not None:
                coach.foto = profile_data.foto
            if profile_data.bio is not None:
                coach.bio = profile_data.bio
            if profile_data.experience is not None:
                coach.experience = profile_data.experience
            
            self.db.commit()
            self.db.refresh(user)
            self.db.refresh(coach)
            
            return UserProfileResponse(
                id=user.id,
                email=user.email,
                nombre=user.nombre,
                foto=coach.foto,
                foto_moto=None,
                nivel=None,
                moto=None,
                role=user.role,
                status=coach.status,
                telefono=user.telefono,
                bio=coach.bio,
                experience=coach.experience,
                certificate_url=coach.certificate_url
            )

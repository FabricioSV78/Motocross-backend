from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.pilot_profile import PilotProfile
from app.models.enums import Role, Status, PilotLevel
from app.schemas.user import UserCreate, UserUpdate, PilotProfileCreate, UpdateUserProfileRequest
from app.core.security import get_password_hash


class UserRepository:
    """
    Repositorio para operaciones CRUD de usuarios
    Capa de acceso a datos
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Obtener lista de usuarios con paginación"""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create(self, user_data: UserCreate) -> User:
        """
        Crear nuevo usuario
        
        Args:
            user_data: Datos del usuario a crear
            
        Returns:
            Usuario creado
        """
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            nombre=user_data.nombre,
            hashed_password=hashed_password,
            role=user_data.role.value if isinstance(user_data.role, Role) else user_data.role,
            status=user_data.status.value if isinstance(user_data.status, Status) else user_data.status,
            nombre_empresa=user_data.nombre_empresa,
            telefono=user_data.telefono
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Actualizar usuario existente
        
        Args:
            user_id: ID del usuario a actualizar
            user_data: Datos a actualizar
            
        Returns:
            Usuario actualizado o None si no existe
        """
        db_user = self.get_by_id(user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Si se actualiza la contraseña, hashearla
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def delete(self, user_id: int) -> bool:
        """
        Eliminar usuario
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        db_user = self.get_by_id(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True
    
    def get_user_with_profile(self, user_id: int) -> Optional[User]:
        """
        Obtener usuario con su perfil de piloto (si existe)
        Usa joinedload para eager loading y evitar N+1 queries
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Usuario con perfil de piloto o None si no existe
        """
        return self.db.query(User).options(
            joinedload(User.pilot_profile)
        ).filter(User.id == user_id).first()
    
    def create_pilot_profile(self, user_id: int, profile_data: PilotProfileCreate) -> PilotProfile:
        """
        Crear perfil de piloto para un usuario
        
        Args:
            user_id: ID del usuario
            profile_data: Datos del perfil
            
        Returns:
            Perfil de piloto creado
        """
        db_profile = PilotProfile(
            user_id=user_id,
            foto=profile_data.foto,
            nivel=profile_data.nivel.value if isinstance(profile_data.nivel, PilotLevel) else profile_data.nivel,
            moto=profile_data.moto
        )
        self.db.add(db_profile)
        self.db.commit()
        self.db.refresh(db_profile)
        return db_profile
    
    def get_pilot_profile(self, user_id: int) -> Optional[PilotProfile]:
        """
        Obtener perfil de piloto por user_id
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Perfil de piloto o None si no existe
        """
        return self.db.query(PilotProfile).filter(PilotProfile.user_id == user_id).first()
    
    def update_user_profile(self, user_id: int, data: UpdateUserProfileRequest) -> Optional[User]:
        """
        Actualizar perfil completo del piloto (User.nombre + PilotProfile)
        HU-06: Editar perfil

        Args:
            user_id: ID del usuario
            data: Datos a actualizar

        Returns:
            Usuario con perfil actualizado, o None si no existe
        """
        user = self.get_user_with_profile(user_id)
        if not user:
            return None

        # Actualizar nombre en el modelo User
        user.nombre = data.nombre

        # Actualizar o crear PilotProfile
        if not user.pilot_profile:
            db_profile = PilotProfile(
                user_id=user_id,
                foto=data.foto,
                foto_moto=data.foto_moto,
                nivel=data.nivel.value if data.nivel else PilotLevel.BEGINNER.value,
                moto=data.moto,
            )
            self.db.add(db_profile)
        else:
            provided_fields = data.model_fields_set
            if "foto" in provided_fields:
                user.pilot_profile.foto = data.foto
            if "foto_moto" in provided_fields:
                user.pilot_profile.foto_moto = data.foto_moto
            if data.nivel is not None:
                user.pilot_profile.nivel = (
                    data.nivel.value if isinstance(data.nivel, PilotLevel) else data.nivel
                )
            if "moto" in provided_fields:
                user.pilot_profile.moto = data.moto

        self.db.commit()
        self.db.refresh(user)
        return user

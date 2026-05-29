from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.enums import Role, Status
from app.repositories.user import UserRepository
from app.repositories.coach_repository import CoachRepository
from app.schemas.user import RegisterRequest, RegisterCompanyRequest, UserCreate, PilotProfileCreate
from app.schemas.coach import RegisterCoachRequest
from app.core.security import verify_password, create_access_token


class AuthService:
    """
    Servicio de autenticación
    Lógica de negocio para login, registro, etc.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.coach_repo = CoachRepository(db)
    
    def register_pilot(self, register_data: RegisterRequest) -> User:
        """
        Registrar nuevo piloto
        
        Reglas de negocio:
        - El email debe ser único
        - Password mínimo 8 caracteres (validado en schema)
        - Contraseña encriptada con bcrypt
        - Role = PILOT
        - Status = ACTIVE
        - Se crea automáticamente un perfil de piloto por defecto
        
        Args:
            register_data: Datos de registro (email, password, nombre)
            
        Returns:
            Usuario creado
            
        Raises:
            HTTPException: Si el email ya existe
        """
        # Verificar si el email ya existe
        existing_user = self.user_repo.get_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )
        
        # Crear usuario con role PILOT y status ACTIVE
        user_data = UserCreate(
            email=register_data.email,
            nombre=register_data.nombre,
            password=register_data.password,
            role=Role.PILOT,
            status=Status.ACTIVE
        )
        
        user = self.user_repo.create(user_data)
        
        # Crear perfil de piloto por defecto
        profile_data = PilotProfileCreate()
        self.user_repo.create_pilot_profile(user.id, profile_data)
        
        return user
    
    def register_company(self, register_data: RegisterCompanyRequest) -> User:
        """
        Registrar nueva empresa
        
        Reglas de negocio:
        - El email debe ser único
        - Password mínimo 8 caracteres (validado en schema)
        - Contraseña encriptada con bcrypt
        - Role = COMPANY
        - Status = PENDING (requiere aprobación de administrador)
        - Las empresas con status PENDING no aparecen en búsquedas
        
        Args:
            register_data: Datos de registro (email, password, nombre_empresa, telefono)
            
        Returns:
            Usuario empresa creado
            
        Raises:
            HTTPException: Si el email ya existe
        """
        # Verificar si el email ya existe
        existing_user = self.user_repo.get_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )
        
        # Crear usuario empresa con role COMPANY y status PENDING
        user_data = UserCreate(
            email=register_data.email,
            nombre=register_data.nombre_empresa,  # Usar nombre_empresa como nombre
            password=register_data.password,
            role=Role.COMPANY,
            status=Status.PENDING,
            nombre_empresa=register_data.nombre_empresa,
            telefono=register_data.telefono
        )
        
        return self.user_repo.create(user_data)

    def register_coach(self, register_data: RegisterCoachRequest) -> User:
        """
        HU-03: Registrar nuevo coach

        Reglas de negocio:
        - El email debe ser único
        - Password mínimo 8 caracteres (validado en schema)
        - Contraseña encriptada con bcrypt
        - Role = COACH
        - Status = PENDING (requiere aprobación de administrador)
        - Se crea automáticamente un registro en tabla coaches

        Args:
            register_data: Datos de registro (email, password, nombre, telefono, experience)

        Returns:
            Usuario coach creado

        Raises:
            HTTPException: Si el email ya existe
        """
        existing_user = self.user_repo.get_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )

        user_data = UserCreate(
            email=register_data.email,
            nombre=register_data.nombre,
            password=register_data.password,
            role=Role.COACH,
            status=Status.PENDING,
            telefono=register_data.telefono,
        )

        user = self.user_repo.create(user_data)

        # Crear registro en tabla coaches
        self.coach_repo.create(user_id=user.id, experience=register_data.experience)

        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Autenticar usuario con email y contraseña
        
        Args:
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Usuario si las credenciales son correctas, None si no
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_token(self, user_id: int) -> str:
        """
        Crear JWT token para un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Token JWT
        """
        return create_access_token(subject=user_id)

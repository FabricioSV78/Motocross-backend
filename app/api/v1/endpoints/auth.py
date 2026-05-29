from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import Token, LoginRequest, LoginResponse, LogoutResponse, RegisterRequest, RegisterCompanyRequest, UserResponse, CompanyResponse
from app.schemas.coach import RegisterCoachRequest, CoachRegisterResponse
from app.services.auth import AuthService
from app.models.enums import Status, Role
from app.api.deps import get_current_active_user
from app.models.user import User


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    HU-01: Registro de piloto
    
    Registrar nuevo piloto en la plataforma
    
    Reglas de negocio:
    - Email debe ser único
    - Password mínimo 8 caracteres
    - Contraseña encriptada con bcrypt
    - Usuario creado con role = PILOT y status = ACTIVE
    
    Body:
    - **email**: Email único del piloto (formato válido)
    - **password**: Contraseña (mínimo 8 caracteres)
    - **nombre**: Nombre del piloto
    
    Returns:
        Usuario creado sin contraseña
        
    Raises:
        400: Si el email ya está registrado
        422: Si los datos no cumplen las validaciones
    """
    auth_service = AuthService(db)
    return auth_service.register_pilot(register_data)


@router.post("/register-company", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def register_company(
    register_data: RegisterCompanyRequest,
    db: Session = Depends(get_db)
):
    """
    HU-02: Registro de empresa
    
    Registrar nueva empresa en la plataforma
    
    Reglas de negocio:
    - Email debe ser único
    - Password mínimo 8 caracteres
    - Contraseña encriptada con bcrypt
    - Usuario creado con role = COMPANY y status = PENDING
    - Las empresas con status PENDING no aparecen en búsquedas hasta ser aprobadas por un admin
    
    Body:
    - **email**: Email único de la empresa (formato válido)
    - **password**: Contraseña (mínimo 8 caracteres)
    - **nombre_empresa**: Nombre de la empresa
    - **telefono**: Teléfono de contacto
    
    Returns:
        Empresa creada sin contraseña, con status PENDING
        
    Raises:
        400: Si el email ya está registrado
        422: Si los datos no cumplen las validaciones
    """
    auth_service = AuthService(db)
    return auth_service.register_company(register_data)


@router.post("/register-coach", response_model=CoachRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_coach(
    register_data: RegisterCoachRequest,
    db: Session = Depends(get_db)
):
    """
    HU-03: Registro de coach

    Registrar nuevo coach en la plataforma.

    Reglas de negocio:
    - Email debe ser único
    - Password mínimo 8 caracteres
    - Contraseña encriptada con bcrypt
    - Usuario creado con role = COACH y status = PENDING
    - Se crea registro en tabla coaches
    - El coach NO puede ofrecer clases hasta que el admin lo apruebe

    Body:
    - **email**: Email único del coach (formato válido)
    - **password**: Contraseña (mínimo 8 caracteres)
    - **nombre**: Nombre del coach
    - **telefono**: Teléfono de contacto
    - **experience**: Experiencia previa (opcional)

    Returns:
        Coach creado con id, email, role y status

    Raises:
        400: Si el email ya está registrado
        422: Si los datos no cumplen las validaciones
    """
    auth_service = AuthService(db)
    user = auth_service.register_coach(register_data)
    return CoachRegisterResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    HU-03: Login de usuario
    
    Autenticar usuario y generar JWT token
    
    Flujo:
    1. Validar credenciales (email + password)
    2. Verificar que el usuario esté activo
    3. Generar JWT token
    4. Retornar token y datos básicos del usuario
    
    Body:
    - **email**: Email del usuario
    - **password**: Contraseña
    
    Returns:
        Token JWT y datos básicos del usuario (id, email, role)
        
    Raises:
        401: Si las credenciales son incorrectas
        400: Si el usuario no está activo
    """
    auth_service = AuthService(db)
    
    # Autenticar usuario
    user = auth_service.authenticate(
        email=login_data.email,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    ALLOWED_STATUSES = {Status.ACTIVE, Status.APPROVED}
    # Los coaches en PENDING pueden iniciar sesión para subir su certificado
    is_pending_coach = (user.role == Role.COACH and user.status == Status.PENDING)
    if user.status not in ALLOWED_STATUSES and not is_pending_coach:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive or pending approval"
        )
    
    # Crear token
    access_token = auth_service.create_token(user.id)
    
    return LoginResponse(
        token=access_token,
        user={"id": user.id, "email": user.email},
        role=user.role,
        status=user.status,
    )


@router.post("/login-oauth", response_model=Token)
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login OAuth2 compatible (para Swagger UI)
    
    Retorna un JWT access token que debe incluirse en el header Authorization
    como: Bearer {token}
    
    - **username**: Email del usuario (OAuth2 usa username, pero aceptamos email)
    - **password**: Contraseña
    """
    auth_service = AuthService(db)
    
    # Autenticar usuario
    user = auth_service.authenticate(
        email=form_data.username,  # OAuth2 usa 'username', pero nosotros usamos email
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != Status.ACTIVE:
        is_pending_coach = (user.role == Role.COACH and user.status == Status.PENDING)
        if not is_pending_coach:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is inactive"
            )
    
    # Crear token
    access_token = auth_service.create_token(user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    HU-04: Logout de usuario
    
    Cerrar sesión del usuario actual.
    
    En sistemas con JWT, el logout se maneja principalmente en el cliente
    eliminando el token. Este endpoint confirma el logout del lado del servidor.
    
    Requiere autenticación (token JWT válido).
    
    En el futuro, este endpoint puede extenderse para:
    - Agregar el token a una blacklist
    - Revocar refresh tokens
    - Registrar auditoría de logout
    - Notificar a otros servicios
    
    Returns:
        Mensaje de confirmación de logout
        
    Raises:
        401: Si el token es inválido o no está presente
    """
    return LogoutResponse(
        message="Logout successful"
    )

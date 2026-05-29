from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings, UPLOAD_DIR
from app.api.v1.api import api_router
from app.db.base import Base  # noqa: F401 — importa todos los modelos
from app.db.session import engine, SessionLocal
from app.models.user import User
from app.models.enums import Role, Status
from app.core.security import get_password_hash

# Crear tablas en la BD al arrancar (CREATE TABLE IF NOT EXISTS)
Base.metadata.create_all(bind=engine)

# Crear directorio de uploads si no existe (ruta absoluta, independiente del CWD)
UPLOAD_DIR.mkdir(exist_ok=True)

# ── Seed: crear admin por defecto si no existe ──────────────────────────────
def _seed_admin() -> None:
    """Garantiza que exista al menos un usuario ADMIN al iniciar el servidor."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin@motocross.com").first()
        if existing is None:
            admin = User(
                email="admin@motocross.com",
                nombre="Administrator",
                hashed_password=get_password_hash("Admin1234!"),
                role=Role.ADMIN.value,
                status=Status.ACTIVE.value,
            )
            db.add(admin)
            db.commit()
            print("✅ Default admin created: admin@motocross.com / Admin1234!")
    finally:
        db.close()

_seed_admin()
# ────────────────────────────────────────────────────────────────────────────

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS - IMPORTANTE: Debe estar ANTES de incluir los routers
# allow_credentials=True es incompatible con allow_origins=["*"] según la spec CORS.
# Los navegadores rechazan Access-Control-Allow-Origin: * cuando se envían credenciales.
# El JWT viaja en el header Authorization (no en cookies), así que no se necesita allow_credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternativa React
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Servir archivos estáticos (fotos subidas por los usuarios)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Captura cualquier excepción no manejada (ej: errores de BD, tablas inexistentes)
    y la convierte en una respuesta JSON 500 que SÍ pasa por el CORS middleware.
    Sin este handler, las excepciones suben hasta ServerErrorMiddleware (que está
    por encima de CORSMiddleware) y la respuesta sale sin el header
    Access-Control-Allow-Origin, bloqueando el browser.
    """
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}"},
    )


@app.get("/")
def root():
    """
    Endpoint raíz
    """
    return {
        "message": "Welcome to Motocross Booking Platform API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

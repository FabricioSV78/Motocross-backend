from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, admin, tracks, companies, coach, reservations


api_router = APIRouter()

# Incluir routers de módulos
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(users.router, prefix="/users", tags=["Usuarios"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administración"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["Pistas"])
api_router.include_router(companies.router, prefix="/companies", tags=["Empresas"])
api_router.include_router(coach.router, prefix="/coach", tags=["Coach"])
api_router.include_router(reservations.router, tags=["Reservas y Pagos"])

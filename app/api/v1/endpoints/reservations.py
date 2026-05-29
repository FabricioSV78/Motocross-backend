"""
Reservation endpoints (router aggregator)
"""

from fastapi import APIRouter

from app.api.v1.endpoints.reservations_calculate import router as calculate_router
from app.api.v1.endpoints.reservations_create import router as create_router
from app.api.v1.endpoints.reservations_list import router as list_router
from app.api.v1.endpoints.reservations_webhook import router as webhook_router


router = APIRouter(prefix="/reservations", tags=["Reservations"])

router.include_router(calculate_router)
router.include_router(create_router)
router.include_router(list_router)
router.include_router(webhook_router)

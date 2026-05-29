from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.reservation_service import ReservationService
from app.services.stripe_service import stripe_service


router = APIRouter()


# ============================================================================
# POST /reservations/webhooks/stripe - Stripe webhook
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Stripe webhook to confirm payments.

    **HU-20: Automatic payment confirmation**

    **Events to handle**:
    - `payment_intent.succeeded` -> set reservation to CONFIRMED
    - `payment_intent.payment_failed` -> set reservation to CANCELLED

    **Security**:
    - Validate webhook signature with STRIPE_WEBHOOK_SECRET
    - Only process authentic Stripe events
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    try:
        event = stripe_service.verify_webhook_signature(payload, signature)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    event_type = event.get("type")
    payment_intent_id = event.get("data", {}).get("object", {}).get("id")

    if event_type == "payment_intent.succeeded":
        try:
            ReservationService.handle_payment_succeeded(db, payment_intent_id)
            return {"status": "success", "message": "Pago confirmado"}
        except HTTPException as e:
            return {"status": "warning", "message": str(e.detail)}

    if event_type == "payment_intent.payment_failed":
        try:
            ReservationService.handle_payment_failed(db, payment_intent_id)
            return {"status": "success", "message": "Pago marcado como fallido"}
        except HTTPException as e:
            return {"status": "warning", "message": str(e.detail)}

    return {"status": "ignored", "message": f"Event type {event_type} not handled"}

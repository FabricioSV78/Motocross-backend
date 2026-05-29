"""
Service para integración con Stripe
"""

import os
from typing import Optional
from app.core.config import settings


class StripeService:
    """
    Servicio para manejar integraciones con Stripe
    
    IMPORTANTE: Las funciones están preparadas para cuando agregues:
    - STRIPE_SECRET_KEY
    - STRIPE_WEBHOOK_SECRET
    
    En tu archivo .env
    """
    
    def __init__(self):
        """Inicializar servicio Stripe (cuando tengas las keys)"""
        self.stripe_secret_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        self.stripe_webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        
        # Si tenemos las keys, importar stripe
        if self.stripe_secret_key:
            try:
                import stripe
                stripe.api_key = self.stripe_secret_key
                self.stripe = stripe
                self.is_configured = True
            except ImportError:
                self.is_configured = False
        else:
            self.is_configured = False
    
    def create_payment_intent(
        self,
        amount: int,  # En centavos (ej: 15400 = $154.00)
        currency: str = "aud",
        description: str = "Motocross Reservation",
        metadata: dict = None,
    ) -> Optional[dict]:
        """
        Crear PaymentIntent en Stripe
        
        Args:
            amount: Monto en centavos
            currency: Moneda
            description: Descripción
            metadata: Datos adicionales
            
        Returns:
            Dict con client_secret y payment_intent_id, o None si no configurado
        """
        if not self.is_configured:
            return {
                "client_secret": "pi_demo_secret_" + str(amount),
                "payment_intent_id": f"pi_{amount}_demo",
                "status": "requires_payment_method",
                "demo_mode": True,
            }
        
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata or {},
            )
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "status": intent.status,
                "demo_mode": False,
            }
        except Exception as e:
            raise ValueError(f"Error creating payment intent: {str(e)}")
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> Optional[dict]:
        """
        Verificar firma de webhook de Stripe
        
        Args:
            payload: Body del webhook
            signature: Header stripe-signature
            
        Returns:
            Event dict si es válido, None si no
        """
        if not self.is_configured:
            # En demo mode, retornar que es válido pero marcar como demo
            return {
                "id": "demo_event",
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_demo"}},
                "demo_mode": True,
            }
        
        try:
            event = self.stripe.Webhook.construct_event(
                payload, signature, self.stripe_webhook_secret
            )
            return event
        except ValueError:
            raise ValueError("Invalid payload")
        except self.stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")
    
    def retrieve_payment_intent(self, payment_intent_id: str) -> Optional[dict]:
        """
        Obtener detalles de un PaymentIntent
        
        Args:
            payment_intent_id: ID del PaymentIntent
            
        Returns:
            Dict con los detalles o None
        """
        if not self.is_configured:
            return {
                "id": payment_intent_id,
                "status": "succeeded",
                "amount": 15400,
                "currency": "aud",
                "demo_mode": True,
            }
        
        try:
            intent = self.stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
            }
        except Exception as e:
            raise ValueError(f"Error retrieving payment intent: {str(e)}")


# Instancia global
stripe_service = StripeService()

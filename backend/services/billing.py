"""
Billing service using Stripe.
Handles subscriptions, invoices, and payment processing.
"""
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    import stripe
except ImportError:
    stripe = None

from .database import DatabaseService, Tenant


# Plan configuration
PLAN_CONFIG = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "queries_per_month": 1000,
        "rate_limit_per_minute": 10,
        "features": ["single_search", "basic_support"],
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "queries_per_month": 10000,
        "rate_limit_per_minute": 60,
        "features": ["single_search", "batch_search", "email_support"],
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 99,
        "queries_per_month": 100000,
        "rate_limit_per_minute": 300,
        "features": ["single_search", "batch_search", "priority_support", "analytics"],
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 499,
        "queries_per_month": 1000000,
        "rate_limit_per_minute": 1000,
        "features": ["single_search", "batch_search", "sso", "dedicated_support", "analytics", "sla"],
    },
}


@dataclass
class SubscriptionInfo:
    """Subscription information."""
    tier: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    stripe_subscription_id: Optional[str]
    stripe_customer_id: Optional[str]


@dataclass
class Invoice:
    """Invoice information."""
    id: str
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    created: datetime
    period_start: datetime
    period_end: datetime
    pdf_url: Optional[str]


class BillingService:
    """Service for billing operations using Stripe."""

    def __init__(
        self,
        db: DatabaseService,
        stripe_secret_key: str,
        stripe_webhook_secret: str,
        price_ids: Dict[str, str],
    ):
        """
        Initialize billing service.

        Args:
            db: Database service instance
            stripe_secret_key: Stripe secret API key
            stripe_webhook_secret: Stripe webhook signing secret
            price_ids: Dict mapping plan tier to Stripe price ID
        """
        if stripe is None:
            raise RuntimeError("stripe not available")

        stripe.api_key = stripe_secret_key
        self.db = db
        self.webhook_secret = stripe_webhook_secret
        self.price_ids = price_ids

    # ==================== CUSTOMER MANAGEMENT ====================

    async def create_customer(
        self,
        tenant_id: str,
        email: str,
        name: str,
        metadata: Dict[str, str] = None,
    ) -> str:
        """
        Create a Stripe customer for a tenant.

        Returns the Stripe customer ID.
        """
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                "tenant_id": tenant_id,
                **(metadata or {}),
            },
        )

        # Update tenant with customer ID
        await self.db.update_tenant(tenant_id, {
            "stripe_customer_id": customer.id,
        })

        return customer.id

    async def get_or_create_customer(
        self,
        tenant: Tenant,
        email: str,
    ) -> str:
        """Get existing customer or create new one."""
        if tenant.stripe_customer_id:
            return tenant.stripe_customer_id

        return await self.create_customer(
            tenant_id=tenant.id,
            email=email,
            name=tenant.name,
        )

    # ==================== SUBSCRIPTION MANAGEMENT ====================

    async def create_subscription(
        self,
        tenant_id: str,
        customer_id: str,
        plan_tier: str,
    ) -> SubscriptionInfo:
        """
        Create a new subscription for a tenant.

        Args:
            tenant_id: The tenant ID
            customer_id: Stripe customer ID
            plan_tier: The plan tier to subscribe to

        Returns:
            SubscriptionInfo with subscription details
        """
        price_id = self.price_ids.get(plan_tier)
        if not price_id:
            raise ValueError(f"Unknown plan tier: {plan_tier}")

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            metadata={"tenant_id": tenant_id},
        )

        # Update tenant
        await self.db.update_tenant_subscription(
            tenant_id=tenant_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription.id,
            plan_tier=plan_tier,
            status=subscription.status,
        )

        return self._subscription_to_info(subscription, plan_tier)

    async def create_checkout_session(
        self,
        tenant_id: str,
        customer_id: str,
        plan_tier: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe Checkout session for subscription.

        Returns the checkout session URL.
        """
        price_id = self.price_ids.get(plan_tier)
        if not price_id:
            raise ValueError(f"Unknown plan tier: {plan_tier}")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id, "plan_tier": plan_tier},
        )

        return session.url

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """
        Create a Stripe Customer Portal session.

        Returns the portal session URL.
        """
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    async def get_subscription(self, tenant: Tenant) -> Optional[SubscriptionInfo]:
        """Get current subscription info for a tenant."""
        if not tenant.stripe_subscription_id:
            return SubscriptionInfo(
                tier="free",
                status="active",
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc),
                cancel_at_period_end=False,
                stripe_subscription_id=None,
                stripe_customer_id=tenant.stripe_customer_id,
            )

        subscription = stripe.Subscription.retrieve(tenant.stripe_subscription_id)
        return self._subscription_to_info(subscription, tenant.plan_tier)

    async def cancel_subscription(
        self,
        tenant_id: str,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> SubscriptionInfo:
        """
        Cancel a subscription.

        Args:
            tenant_id: The tenant ID
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of period; if False, cancel immediately

        Returns:
            Updated subscription info
        """
        if at_period_end:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            subscription = stripe.Subscription.cancel(subscription_id)

        # Update tenant
        tenant = await self.db.get_tenant(tenant_id)
        await self.db.update_tenant(tenant_id, {
            "subscription_status": subscription.status,
        })

        return self._subscription_to_info(subscription, tenant.plan_tier if tenant else "free")

    async def change_plan(
        self,
        tenant_id: str,
        subscription_id: str,
        new_plan_tier: str,
    ) -> SubscriptionInfo:
        """
        Change subscription to a different plan.

        Handles prorations automatically.
        """
        new_price_id = self.price_ids.get(new_plan_tier)
        if not new_price_id:
            raise ValueError(f"Unknown plan tier: {new_plan_tier}")

        # Get current subscription
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Update subscription with new price
        subscription = stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": new_price_id,
            }],
            proration_behavior="create_prorations",
        )

        # Update tenant
        await self.db.update_tenant(tenant_id, {
            "plan_tier": new_plan_tier,
            "subscription_status": subscription.status,
        })

        return self._subscription_to_info(subscription, new_plan_tier)

    # ==================== INVOICES ====================

    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> List[Invoice]:
        """Get recent invoices for a customer."""
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
        return [self._invoice_to_model(inv) for inv in invoices.data]

    async def get_upcoming_invoice(self, customer_id: str) -> Optional[Invoice]:
        """Get the upcoming invoice for a customer."""
        try:
            invoice = stripe.Invoice.upcoming(customer=customer_id)
            return self._invoice_to_model(invoice)
        except stripe.error.InvalidRequestError:
            return None

    # ==================== WEBHOOK HANDLING ====================

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify and parse a Stripe webhook.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value

        Returns:
            Parsed webhook event

        Raises:
            ValueError: If signature is invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return event
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature")

    async def handle_webhook(self, event: Dict[str, Any]) -> bool:
        """
        Handle a Stripe webhook event.

        Args:
            event: Parsed webhook event

        Returns:
            True if handled successfully
        """
        event_type = event["type"]
        data = event["data"]["object"]

        # Log the event
        await self.db.log_billing_event(
            event_id=event["id"],
            event_type=event_type,
            payload=event,
        )

        # Handle specific events
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(data)

        # Mark as processed
        await self.db.mark_billing_event_processed(event["id"])
        return True

    async def _handle_subscription_created(self, data: Dict[str, Any]) -> None:
        """Handle subscription.created event."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await self.db.update_tenant(tenant_id, {
                "stripe_subscription_id": data["id"],
                "subscription_status": data["status"],
            })

    async def _handle_subscription_updated(self, data: Dict[str, Any]) -> None:
        """Handle subscription.updated event."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await self.db.update_tenant(tenant_id, {
                "subscription_status": data["status"],
            })

    async def _handle_subscription_deleted(self, data: Dict[str, Any]) -> None:
        """Handle subscription.deleted event."""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await self.db.update_tenant(tenant_id, {
                "subscription_status": "canceled",
                "plan_tier": "free",
            })

    async def _handle_invoice_paid(self, data: Dict[str, Any]) -> None:
        """Handle invoice.paid event."""
        # Could send receipt email, update analytics, etc.
        pass

    async def _handle_payment_failed(self, data: Dict[str, Any]) -> None:
        """Handle invoice.payment_failed event."""
        customer_id = data.get("customer")
        if customer_id:
            # Find tenant by customer ID and update status
            # Would need additional DB query
            pass

    # ==================== HELPERS ====================

    def _subscription_to_info(
        self,
        subscription: Any,
        plan_tier: str,
    ) -> SubscriptionInfo:
        """Convert Stripe subscription to SubscriptionInfo."""
        return SubscriptionInfo(
            tier=plan_tier,
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(
                subscription.current_period_start, tz=timezone.utc
            ),
            current_period_end=datetime.fromtimestamp(
                subscription.current_period_end, tz=timezone.utc
            ),
            cancel_at_period_end=subscription.cancel_at_period_end,
            stripe_subscription_id=subscription.id,
            stripe_customer_id=subscription.customer,
        )

    def _invoice_to_model(self, invoice: Any) -> Invoice:
        """Convert Stripe invoice to Invoice model."""
        return Invoice(
            id=invoice.id,
            amount_due=invoice.amount_due,
            amount_paid=invoice.amount_paid,
            currency=invoice.currency,
            status=invoice.status,
            created=datetime.fromtimestamp(invoice.created, tz=timezone.utc),
            period_start=datetime.fromtimestamp(invoice.period_start, tz=timezone.utc),
            period_end=datetime.fromtimestamp(invoice.period_end, tz=timezone.utc),
            pdf_url=invoice.invoice_pdf,
        )

    @staticmethod
    def get_plan_config(tier: str) -> Dict[str, Any]:
        """Get plan configuration by tier."""
        return PLAN_CONFIG.get(tier, PLAN_CONFIG["free"])

    @staticmethod
    def get_all_plans() -> Dict[str, Dict[str, Any]]:
        """Get all plan configurations."""
        return PLAN_CONFIG

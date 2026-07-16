"""Integración con Stripe: checkout, portal de cliente y webhooks.

Degradación elegante: sin STRIPE_SECRET_KEY configurada, los planes de pago
devuelven 503 pero el plan free y las cuotas funcionan con normalidad.
"""

from datetime import datetime, timezone

from app_service.config import get_settings
from app_service.providers.database.models import Plan, User
from app_service.providers.database.models.billing import (
    StripeWebhookEvent,
    Subscription,
)


class BillingError(Exception):
    pass


class BillingService:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.settings = get_settings()

    # ── helpers ──
    def _stripe(self):
        if not self.settings.stripe_secret_key:
            raise BillingError("Stripe no está configurado (STRIPE_SECRET_KEY)")
        import stripe
        stripe.api_key = self.settings.stripe_secret_key
        return stripe

    def _price_to_plan(self, price_id: str) -> str | None:
        if price_id == self.settings.stripe_price_starter:
            return "starter"
        if price_id == self.settings.stripe_price_pro:
            return "pro"
        with self.db_session_factory() as db:
            plan = db.query(Plan).filter(Plan.stripe_price_id == price_id).first()
            return plan.code if plan else None

    def _plan_to_price(self, plan_code: str) -> str | None:
        if plan_code == "starter":
            return self.settings.stripe_price_starter or None
        if plan_code == "pro":
            return self.settings.stripe_price_pro or None
        return None

    def list_plans(self) -> list[dict]:
        with self.db_session_factory() as db:
            plans = db.query(Plan).filter(Plan.active == True).all()  # noqa: E712
            return [
                {
                    "code": p.code,
                    "name": p.name,
                    "monthly_seconds": p.monthly_seconds,
                    "monthly_hours": round(p.monthly_seconds / 3600, 1),
                    "price_eur_cents": p.price_eur_cents,
                }
                for p in plans
            ]

    # ── checkout / portal ──
    def create_checkout_session(self, user: User, plan_code: str) -> str:
        stripe = self._stripe()
        price_id = self._plan_to_price(plan_code)
        if not price_id:
            raise BillingError(f"Plan sin precio de Stripe configurado: {plan_code}")

        customer_id = self._ensure_customer(stripe, user)
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=user.id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{self.settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{self.settings.frontend_url}/billing/cancelled",
        )
        return session.url

    def create_portal_session(self, user: User) -> str:
        stripe = self._stripe()
        if not user.stripe_customer_id:
            raise BillingError("El usuario no tiene cliente de Stripe")
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{self.settings.frontend_url}/billing",
        )
        return session.url

    def _ensure_customer(self, stripe, user: User) -> str:
        if user.stripe_customer_id:
            return user.stripe_customer_id
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        with self.db_session_factory() as db:
            row = db.get(User, user.id)
            row.stripe_customer_id = customer.id
            db.commit()
        return customer.id

    # ── webhook ──
    def handle_webhook(self, payload: bytes, signature: str) -> dict:
        stripe = self._stripe()
        if not self.settings.stripe_webhook_secret:
            raise BillingError("STRIPE_WEBHOOK_SECRET no configurado")
        event = stripe.Webhook.construct_event(
            payload, signature, self.settings.stripe_webhook_secret
        )

        # Idempotencia
        with self.db_session_factory() as db:
            if db.get(StripeWebhookEvent, event["id"]):
                return {"status": "duplicate"}
            db.add(StripeWebhookEvent(stripe_event_id=event["id"], type=event["type"]))
            db.commit()

        etype = event["type"]
        obj = event["data"]["object"]

        if etype == "checkout.session.completed":
            self._on_checkout_completed(stripe, obj)
        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            self._sync_subscription(obj)
        elif etype == "customer.subscription.deleted":
            self._on_subscription_deleted(obj)
        elif etype == "invoice.payment_failed":
            self._on_payment_failed(obj)

        return {"status": "processed", "type": etype}

    def _user_by_customer(self, db, customer_id: str) -> User | None:
        return db.query(User).filter(User.stripe_customer_id == customer_id).first()

    def _on_checkout_completed(self, stripe, session: dict) -> None:
        customer_id = session.get("customer")
        user_id = session.get("client_reference_id")
        with self.db_session_factory() as db:
            user = db.get(User, user_id) if user_id else self._user_by_customer(db, customer_id)
            if user and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id
                db.commit()
        sub_id = session.get("subscription")
        if sub_id:
            sub = stripe.Subscription.retrieve(sub_id)
            self._sync_subscription(sub)

    def _sync_subscription(self, sub: dict) -> None:
        customer_id = sub.get("customer")
        items = (sub.get("items") or {}).get("data") or []
        price_id = items[0]["price"]["id"] if items else None
        plan_code = self._price_to_plan(price_id) if price_id else None
        if plan_code is None:
            return

        def _ts(key):
            val = sub.get(key)
            # API nueva: los timestamps de periodo viven en el item
            if val is None and items:
                val = items[0].get(key)
            return datetime.fromtimestamp(val, tz=timezone.utc).replace(tzinfo=None) if val else datetime.utcnow()

        with self.db_session_factory() as db:
            user = self._user_by_customer(db, customer_id)
            if user is None:
                return
            row = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == sub["id"])
                .first()
            )
            if row is None:
                # Reutilizar/reemplazar la sub actual del usuario
                row = (
                    db.query(Subscription)
                    .filter(Subscription.user_id == user.id)
                    .order_by(Subscription.created_at.desc())
                    .first()
                )
                if row is None:
                    row = Subscription(user_id=user.id, plan_code=plan_code,
                                       current_period_start=datetime.utcnow(),
                                       current_period_end=datetime.utcnow())
                    db.add(row)
                row.stripe_subscription_id = sub["id"]
            row.plan_code = plan_code
            row.status = "active" if sub.get("status") in ("active", "trialing") else str(sub.get("status"))
            row.current_period_start = _ts("current_period_start")
            row.current_period_end = _ts("current_period_end")
            row.cancel_at_period_end = bool(sub.get("cancel_at_period_end"))
            db.commit()

    def _on_subscription_deleted(self, sub: dict) -> None:
        from app_service.services.quota import _month_period
        with self.db_session_factory() as db:
            row = (
                db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == sub["id"])
                .first()
            )
            if row is None:
                return
            start, end = _month_period()
            row.plan_code = "free"
            row.status = "active"
            row.stripe_subscription_id = None
            row.current_period_start = start
            row.current_period_end = end
            row.cancel_at_period_end = False
            db.commit()

    def _on_payment_failed(self, invoice: dict) -> None:
        customer_id = invoice.get("customer")
        with self.db_session_factory() as db:
            user = self._user_by_customer(db, customer_id)
            if user is None:
                return
            row = (
                db.query(Subscription)
                .filter(Subscription.user_id == user.id)
                .order_by(Subscription.created_at.desc())
                .first()
            )
            if row is not None:
                row.status = "past_due"
                db.commit()

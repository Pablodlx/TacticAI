from fastapi import APIRouter, Depends, HTTPException, Request

from app_service.api.deps import get_current_user, get_job_service
from app_service.providers.database.models import User
from app_service.services.billing import BillingError, BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


def _billing(service=Depends(get_job_service)) -> BillingService:
    return BillingService(db_session_factory=service.db_session_factory)


@router.get("/plans")
def list_plans(billing: BillingService = Depends(_billing)):
    return {"plans": billing.list_plans()}


@router.get("/usage")
def get_usage(
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    if service.quota_service is None:
        raise HTTPException(status_code=503, detail="Cuotas no disponibles")
    return service.quota_service.get_usage(user.id)


@router.post("/checkout-session")
def create_checkout(
    payload: dict,
    user: User = Depends(get_current_user),
    billing: BillingService = Depends(_billing),
):
    plan = payload.get("plan")
    if plan not in ("starter", "pro"):
        raise HTTPException(status_code=400, detail="plan debe ser 'starter' o 'pro'")
    try:
        url = billing.create_checkout_session(user, plan)
    except BillingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"url": url}


@router.post("/portal-session")
def create_portal(
    user: User = Depends(get_current_user),
    billing: BillingService = Depends(_billing),
):
    try:
        url = billing.create_portal_session(user)
    except BillingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, billing: BillingService = Depends(_billing)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        return billing.handle_webhook(payload, signature)
    except BillingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=400, detail="webhook inválido")

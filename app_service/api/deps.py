from fastapi import Depends, HTTPException, Request

from app_service.providers.database.models import User
from app_service.security import decode_access_token
from app_service.services.auth import AuthService
from app_service.services.jobs import JobService

job_service_singleton: JobService | None = None
auth_service_singleton: AuthService | None = None


def set_job_service(service: JobService) -> None:
    global job_service_singleton
    job_service_singleton = service


def get_job_service() -> JobService:
    if job_service_singleton is None:
        raise RuntimeError("JobService not initialized")
    return job_service_singleton


def set_auth_service(service: AuthService) -> None:
    global auth_service_singleton
    auth_service_singleton = service


def get_auth_service() -> AuthService:
    if auth_service_singleton is None:
        raise RuntimeError("AuthService not initialized")
    return auth_service_singleton


def _extract_token(request: Request) -> str | None:
    """Acepta el access token por header Authorization o por cookie.

    La cookie la usa el frontend Next.js (httpOnly, seteada por su BFF);
    el header queda para clientes API directos.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return request.cookies.get("te_access")


def get_current_user(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    user = auth.get_user(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no válido")
    return user

from fastapi import APIRouter, Depends, HTTPException

from app_service.api.deps import get_auth_service, get_current_user
from app_service.providers.database.models import User
from app_service.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app_service.services.auth import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at.isoformat(),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        auth.register(payload.email, payload.password, payload.full_name)
        _, access, refresh = auth.login(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        _, access, refresh = auth.login(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
    try:
        access, new_refresh = auth.refresh(payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
    auth.logout(payload.refresh_token)


@me_router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@me_router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    updated = auth.update_profile(user.id, payload.full_name)
    return _user_response(updated)

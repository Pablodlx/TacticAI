"""Tests del sistema de auth (registro, login, JWT, rotación de refresh)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app_service.providers.database.models import Base
from app_service.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app_service.services.auth import AuthError, AuthService


@pytest.fixture
def auth_service():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return AuthService(db_session_factory=factory)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("secreta123")
        assert h != "secreta123"
        assert verify_password("secreta123", h)
        assert not verify_password("otra", h)


class TestJWT:
    def test_roundtrip(self):
        token = create_access_token("user-42")
        assert decode_access_token(token) == "user-42"

    def test_invalid_token(self):
        assert decode_access_token("garbage") is None


class TestAuthService:
    def test_register_and_login(self, auth_service):
        user = auth_service.register("A@B.com", "password123")
        assert user.email == "a@b.com"  # normalizado
        logged, access, refresh = auth_service.login("a@b.com", "password123")
        assert logged.id == user.id
        assert decode_access_token(access) == user.id
        assert refresh

    def test_duplicate_email(self, auth_service):
        auth_service.register("a@b.com", "password123")
        with pytest.raises(AuthError):
            auth_service.register("A@B.COM", "password456")

    def test_bad_credentials(self, auth_service):
        auth_service.register("a@b.com", "password123")
        with pytest.raises(AuthError):
            auth_service.login("a@b.com", "mala")

    def test_refresh_rotation(self, auth_service):
        auth_service.register("a@b.com", "password123")
        _, _, refresh = auth_service.login("a@b.com", "password123")
        access2, refresh2 = auth_service.refresh(refresh)
        assert decode_access_token(access2)
        # El token viejo queda revocado
        with pytest.raises(AuthError):
            auth_service.refresh(refresh)
        # El nuevo funciona
        auth_service.refresh(refresh2)

    def test_logout_revokes(self, auth_service):
        auth_service.register("a@b.com", "password123")
        _, _, refresh = auth_service.login("a@b.com", "password123")
        auth_service.logout(refresh)
        with pytest.raises(AuthError):
            auth_service.refresh(refresh)

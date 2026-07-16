"""Registro, login y rotación de refresh tokens."""

from datetime import datetime, timedelta

from app_service.config import get_settings
from app_service.providers.database.models import RefreshToken, User
from app_service.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class AuthError(Exception):
    """Error de autenticación (credenciales inválidas, token revocado...)."""


class AuthService:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def register(self, email: str, password: str, full_name: str | None = None) -> User:
        email = email.strip().lower()
        with self.db_session_factory() as db:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                raise AuthError("Ya existe una cuenta con ese email")
            user = User(email=email, password_hash=hash_password(password), full_name=full_name)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Devuelve (user, access_token, refresh_token)."""
        email = email.strip().lower()
        with self.db_session_factory() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user or not verify_password(password, user.password_hash):
                raise AuthError("Email o contraseña incorrectos")
            if not user.is_active:
                raise AuthError("Cuenta desactivada")
            refresh = self._issue_refresh_token(db, user.id)
            db.commit()
            db.refresh(user)
            return user, create_access_token(user.id), refresh

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rota el refresh token. Devuelve (access_token, refresh_token_nuevo)."""
        token_hash = hash_refresh_token(refresh_token)
        with self.db_session_factory() as db:
            record = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == token_hash)
                .first()
            )
            if (
                record is None
                or record.revoked_at is not None
                or record.expires_at < datetime.utcnow()
            ):
                raise AuthError("Refresh token inválido o expirado")
            record.revoked_at = datetime.utcnow()
            new_refresh = self._issue_refresh_token(db, record.user_id)
            user_id = record.user_id
            db.commit()
            return create_access_token(user_id), new_refresh

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        with self.db_session_factory() as db:
            record = (
                db.query(RefreshToken)
                .filter(RefreshToken.token_hash == token_hash)
                .first()
            )
            if record and record.revoked_at is None:
                record.revoked_at = datetime.utcnow()
                db.commit()

    def get_user(self, user_id: str) -> User | None:
        with self.db_session_factory() as db:
            return db.get(User, user_id)

    def update_profile(self, user_id: str, full_name: str | None) -> User:
        with self.db_session_factory() as db:
            user = db.get(User, user_id)
            if not user:
                raise AuthError("Usuario no encontrado")
            if full_name is not None:
                user.full_name = full_name
            db.commit()
            db.refresh(user)
            return user

    def _issue_refresh_token(self, db, user_id: str) -> str:
        settings = get_settings()
        token, token_hash = generate_refresh_token()
        db.add(RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_ttl_days),
        ))
        return token

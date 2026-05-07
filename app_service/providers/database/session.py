from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app_service.config import Settings
from app_service.providers.database.base import Base


def build_session_factory(settings: Settings) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def build_ephemeral_test_session_factory(database_url: str) -> sessionmaker[Session]:
    """
    Solo para tests efímeros/in-memory donde no se ejecuta Alembic.
    En flujo normal app/CI usar siempre migraciones Alembic.
    """
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app_service.config import Settings
from app_service.providers.database.base import Base


def build_session_factory(settings: Settings) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


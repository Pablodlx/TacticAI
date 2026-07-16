import os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app_service.api.deps import set_auth_service, set_job_service
from app_service.api.routes import router
from app_service.api.routes_auth import me_router, router as auth_router
from app_service.api.routes_analytics import router as analytics_router
from app_service.api.routes_billing import router as billing_router
from app_service.api.routes_matches import router as matches_router
from app_service.config import get_settings
from app_service.services.auth import AuthService
from app_service.services.matches import MatchIngestService
from app_service.services.quota import QuotaService
from app_service.services.factory import (
    build_analysis_runner,
    build_queue,
    build_session,
    build_storage,
)
from app_service.services.jobs import JobService


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TacticEYE API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = build_storage(settings)
    queue = build_queue(settings)
    session_factory = build_session(settings)
    # Only the sync backend runs analysis inside the web process;
    # other backends (pubsub, redis) offload to the worker service.
    analysis_runner = build_analysis_runner(settings) if settings.queue_backend == "sync" else None

    service = JobService(
        db_session_factory=session_factory,
        storage=storage,
        queue=queue,
        analysis_runner=analysis_runner,
        local_workspace=os.path.join(settings.local_storage_path, "workspace"),
        match_ingest=MatchIngestService(db_session_factory=session_factory, storage=storage),
        quota_service=QuotaService(db_session_factory=session_factory),
    )
    set_job_service(service)
    set_auth_service(AuthService(db_session_factory=session_factory))

    # Esta es la API pura del producto: la interfaz vive en el frontend
    # Next.js (tacticeye-web, puerto 3000). Un GET a "/" deja claro qué es
    # esto en vez de servir por error la SPA legacy del monolito app.py.
    @app.get("/")
    def root():
        return {"service": "TacticEYE API", "docs": "/docs", "health": "/health"}

    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(matches_router)
    app.include_router(billing_router)
    app.include_router(analytics_router)
    return app


app = create_app()
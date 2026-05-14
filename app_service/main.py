import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app_service.api.deps import set_job_service
from app_service.api.routes import router
from app_service.config import get_settings
from app_service.services.factory import (
    build_analysis_runner,
    build_queue,
    build_session,
    build_storage,
)
from app_service.services.jobs import JobService


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TacticEYE2 Dual API")

    templates = Jinja2Templates(directory="templates")

    storage = build_storage(settings)
    queue = build_queue(settings)
    session_factory = build_session(settings)
    analysis_runner = build_analysis_runner(settings)

    service = JobService(
        db_session_factory=session_factory,
        storage=storage,
        queue=queue,
        analysis_runner=analysis_runner,
        local_workspace=os.path.join(settings.local_storage_path, "workspace"),
    )
    set_job_service(service)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request, "index.html")

    app.include_router(router)
    return app


app = create_app()
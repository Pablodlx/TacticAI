from app_service.services.factory import build_analysis_runner, build_queue, build_session, build_storage
from app_service.services.jobs import JobService
from app_service.config import get_settings


def run_worker() -> None:
    settings = get_settings()
    storage = build_storage(settings)
    queue = build_queue(settings)
    session_factory = build_session(settings)
    analysis_runner = build_analysis_runner(settings)
    service = JobService(
        db_session_factory=session_factory,
        storage=storage,
        queue=queue,
        analysis_runner=analysis_runner,
        local_workspace=f"{settings.local_storage_path}/workspace",
    )
    queue.consume_forever(service.process_payload)


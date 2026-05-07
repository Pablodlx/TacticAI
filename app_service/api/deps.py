from app_service.services.jobs import JobService

job_service_singleton: JobService | None = None


def set_job_service(service: JobService) -> None:
    global job_service_singleton
    job_service_singleton = service


def get_job_service() -> JobService:
    if job_service_singleton is None:
        raise RuntimeError("JobService not initialized")
    return job_service_singleton


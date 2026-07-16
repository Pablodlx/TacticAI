from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app_service.api.deps import get_current_user, get_job_service
from app_service.providers.database.models import User

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}

@router.post("/health")
def health_post():
    return {"ok": True}


def _get_owned_job(service, job_id: str, user: User):
    job = service.get_job(job_id)
    if not job or (job.user_id is not None and job.user_id != user.id):
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/jobs/upload-url")
def get_upload_url(
    filename: str = Query(...),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    try:
        upload_url, input_uri = service.get_upload_url(filename)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Signed URLs not supported in this environment")
    return {"upload_url": upload_url, "input_uri": input_uri}


@router.post("/jobs/upload")
async def upload_video(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    # Streaming a disco por trozos: un vídeo de partido completo puede pesar
    # varios GB, y cargarlo entero en memoria (como se hacía antes) puede
    # agotar la RAM del sistema.
    input_uri = await service.upload_input_stream(file.filename, file)
    duration = service.probe_duration(input_uri)
    return {"input_uri": input_uri, "duration_seconds": duration}


@router.post("/jobs")
def create_job(
    payload: dict,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    input_uri = payload.get("input_uri")
    if not input_uri:
        raise HTTPException(status_code=400, detail="input_uri required")

    # Cuota: la duración se sondeó en el upload; verificar saldo antes de crear
    duration = payload.get("duration_seconds") or service.probe_duration(input_uri) or 0.0
    if service.quota_service is not None:
        remaining = service.quota_service.remaining_seconds(user.id)
        if duration > remaining:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Horas de análisis insuficientes",
                    "remaining_seconds": remaining,
                    "required_seconds": duration,
                },
            )

    job_id = service.create_job(
        input_uri=input_uri,
        extra_config=payload.get("config", {}),
        user_id=user.id,
        video_duration_seconds=duration,
        charged_seconds=duration if service.quota_service is not None else None,
    )
    if service.quota_service is not None and duration:
        service.quota_service.debit(user.id, job_id, duration)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    job = _get_owned_job(service, job_id, user)
    return {
        "id": job.id,
        "status": job.status,
        "input_uri": job.input_uri,
        "output_uri": job.output_uri,
        "result_json_uri": job.result_json_uri,
        "error_message": job.error_message,
        "progress_pct": job.progress_pct,
        "video_duration_seconds": job.video_duration_seconds,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/jobs/{job_id}/partial")
def get_job_partial(
    job_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    _get_owned_job(service, job_id, user)
    raw = service.storage.read_text_safe(f"partials/{job_id}.json")
    if raw is None:
        return {"available": False}
    import json
    try:
        return {"available": True, **json.loads(raw)}
    except Exception:
        return {"available": False}


@router.get("/jobs/{job_id}/results")
def get_job_results(
    job_id: str,
    user: User = Depends(get_current_user),
    service=Depends(get_job_service),
):
    job = _get_owned_job(service, job_id, user)
    if job.status != "completed" or not job.result_json_uri:
        return {"status": job.status, "result": None}
    return {"status": job.status, "result_uri": job.result_json_uri, "result": service.storage.read_text(job.result_json_uri)}

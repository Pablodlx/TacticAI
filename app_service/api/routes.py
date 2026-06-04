from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app_service.api.deps import get_job_service

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}

@router.post("/health")
def health_post():
    return {"ok": True}


@router.get("/jobs/upload-url")
def get_upload_url(filename: str = Query(...), service=Depends(get_job_service)):
    try:
        upload_url, input_uri = service.get_upload_url(filename)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Signed URLs not supported in this environment")
    return {"upload_url": upload_url, "input_uri": input_uri}


@router.post("/jobs/upload")
async def upload_video(file: UploadFile = File(...), service=Depends(get_job_service)):
    data = await file.read()
    input_uri = service.upload_input(file.filename, data)
    return {"input_uri": input_uri}


@router.post("/jobs")
def create_job(payload: dict, service=Depends(get_job_service)):
    input_uri = payload.get("input_uri")
    if not input_uri:
        raise HTTPException(status_code=400, detail="input_uri required")
    job_id = service.create_job(input_uri=input_uri, extra_config=payload.get("config", {}))
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, service=Depends(get_job_service)):
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "id": job.id,
        "status": job.status,
        "input_uri": job.input_uri,
        "output_uri": job.output_uri,
        "result_json_uri": job.result_json_uri,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/jobs/{job_id}/partial")
def get_job_partial(job_id: str, service=Depends(get_job_service)):
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    raw = service.storage.read_text_safe(f"partials/{job_id}.json")
    if raw is None:
        return {"available": False}
    import json
    try:
        return {"available": True, **json.loads(raw)}
    except Exception:
        return {"available": False}


@router.get("/jobs/{job_id}/results")
def get_job_results(job_id: str, service=Depends(get_job_service)):
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "completed" or not job.result_json_uri:
        return {"status": job.status, "result": None}
    return {"status": job.status, "result_uri": job.result_json_uri, "result": service.storage.read_text(job.result_json_uri)}


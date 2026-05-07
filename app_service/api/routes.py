from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app_service.api.deps import get_job_service

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}

@router.post("/health")
def health_post():
    return {"ok": True}


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


@router.get("/jobs/{job_id}/results")
def get_job_results(job_id: str, service=Depends(get_job_service)):
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "completed" or not job.result_json_uri:
        return {"status": job.status, "result": None}
    return {"status": job.status, "result_uri": job.result_json_uri, "result": service.storage.read_text(job.result_json_uri)}


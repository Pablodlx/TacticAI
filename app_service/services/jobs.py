import json
import os
import shutil
import tempfile
import traceback
import uuid
from datetime import datetime

from app_service.providers.analysis.base import AnalysisRunner
from app_service.providers.database.base import Job
from app_service.providers.queue.base import QueueProvider
from app_service.providers.queue.sync import SyncQueueProvider
from app_service.providers.storage.base import StorageProvider


class JobService:
    def __init__(
        self,
        db_session_factory,
        storage: StorageProvider,
        queue: QueueProvider,
        analysis_runner: AnalysisRunner,
        local_workspace: str,
    ):
        self.db_session_factory = db_session_factory
        self.storage = storage
        self.queue = queue
        self.analysis_runner = analysis_runner
        self.local_workspace = local_workspace
        os.makedirs(self.local_workspace, exist_ok=True)

    def upload_input(self, filename: str, content: bytes) -> str:
        safe = filename.replace("/", "_")
        name = f"inputs/{uuid.uuid4()}_{safe}"
        return self.storage.upload_bytes(content, name)

    def create_job(self, input_uri: str, extra_config: dict | None = None) -> str:
        job_id = str(uuid.uuid4())
        payload = {"job_id": job_id, "input_uri": input_uri, "config": extra_config or {}}
        with self.db_session_factory() as db:
            job = Job(id=job_id, status="pending", input_uri=input_uri)
            db.add(job)
            db.commit()
        self.queue.enqueue(payload)
        if isinstance(self.queue, SyncQueueProvider):
            item = self.queue.pop_nowait()
            if item:
                self.process_payload(item)
        return job_id

    def get_job(self, job_id: str) -> Job | None:
        with self.db_session_factory() as db:
            return db.get(Job, job_id)

    def process_payload(self, payload: dict) -> None:
        job_id = payload["job_id"]
        input_uri = payload["input_uri"]
        with self.db_session_factory() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        tmp_dir = tempfile.mkdtemp(prefix=f"job_{job_id}_", dir=self.local_workspace)
        local_video = os.path.join(tmp_dir, "input.mp4")
        output_dir = os.path.join(tmp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        try:
            self.storage.download_to_path(input_uri, local_video)
            result = self.analysis_runner.run(job_id=job_id, local_input_path=local_video, output_dir=output_dir)
            result_path = os.path.join(tmp_dir, "result.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f)

            archive_base = os.path.join(tmp_dir, f"{job_id}_outputs")
            archive_path = shutil.make_archive(archive_base, "zip", output_dir)
            output_uri = self.storage.upload_file(archive_path, f"outputs/{job_id}.zip")
            result_uri = self.storage.upload_file(result_path, f"results/{job_id}.json")
            with self.db_session_factory() as db:
                job = db.get(Job, job_id)
                if job:
                    job.status = "completed"
                    job.output_uri = output_uri
                    job.result_json_uri = result_uri
                    job.finished_at = datetime.utcnow()
                    db.commit()
        except Exception as exc:
            with self.db_session_factory() as db:
                job = db.get(Job, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = f"{exc}\n{traceback.format_exc()}"
                    job.finished_at = datetime.utcnow()
                    db.commit()


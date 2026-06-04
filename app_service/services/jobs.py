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


def _summary_to_partial(summary: dict, batch_idx: int) -> dict:
    pct = summary.get("possession", {}).get("percent_by_team", {})
    secs = summary.get("possession", {}).get("seconds_by_team", {})
    passes = summary.get("passes", {}).get("by_team", {})
    progress = summary.get("progress", {})
    alerts = summary.get("alerts", [])
    return {
        "batch_idx": batch_idx,
        "total_frames": progress.get("total_frames", 0),
        "total_seconds": progress.get("total_seconds", 0),
        "possession_percent": [pct.get(0, 0), pct.get(1, 0)],
        "possession_seconds": [secs.get(0, 0), secs.get(1, 0)],
        "passes": [passes.get(0, 0), passes.get(1, 0)],
        "alerts": alerts[-10:] if alerts else [],
    }


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

    def get_upload_url(self, filename: str) -> tuple[str, str]:
        safe = filename.replace("/", "_")
        name = f"inputs/{uuid.uuid4()}_{safe}"
        return self.storage.generate_upload_signed_url(name)

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

            def on_batch_complete(match_id, batch_idx, chunk_output, match_state, processor=None):
                try:
                    summary = match_state.get_summary()
                    partial = _summary_to_partial(summary, batch_idx)
                    if processor is not None:
                        st = getattr(processor, "spatial_tracker", None)
                        if st is not None:
                            hm0 = st.export_heatmap(team_id=0, normalize=True)
                            hm1 = st.export_heatmap(team_id=1, normalize=True)
                            if hm0 is not None:
                                partial["heatmap_team_0"] = hm0.tolist()
                            if hm1 is not None:
                                partial["heatmap_team_1"] = hm1.tolist()
                    self.storage.upload_text(json.dumps(partial), f"partials/{job_id}.json")
                except Exception:
                    pass

            result = self.analysis_runner.run(
                job_id=job_id,
                local_input_path=local_video,
                output_dir=output_dir,
                on_batch_complete=on_batch_complete,
            )
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


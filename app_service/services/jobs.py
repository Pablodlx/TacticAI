import json
import os
import shutil
import tempfile
import threading
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
        analysis_runner: AnalysisRunner | None,
        local_workspace: str,
        match_ingest=None,
        quota_service=None,
    ):
        self.db_session_factory = db_session_factory
        self.storage = storage
        self.queue = queue
        self.analysis_runner = analysis_runner
        self.local_workspace = local_workspace
        self.match_ingest = match_ingest
        self.quota_service = quota_service
        os.makedirs(self.local_workspace, exist_ok=True)

    def upload_input(self, filename: str, content: bytes) -> str:
        safe = filename.replace("/", "_")
        name = f"inputs/{uuid.uuid4()}_{safe}"
        return self.storage.upload_bytes(content, name)

    async def upload_input_stream(self, filename: str, file, chunk_size: int = 8 * 1024 * 1024) -> str:
        """Sube un UploadFile por trozos, sin cargar el vídeo entero en RAM.

        Necesario para vídeos de varios GB: leer todo con `await file.read()`
        (como hacía antes) duplica el archivo completo en memoria del proceso
        Python — con un vídeo de partido de 6GB eso agota la RAM disponible.
        """
        safe = filename.replace("/", "_")
        name = f"inputs/{uuid.uuid4()}_{safe}"
        with self.storage.open_writer(name) as writer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                writer.write(chunk)
            uri = writer.uri
        return uri

    def get_upload_url(self, filename: str) -> tuple[str, str]:
        safe = filename.replace("/", "_")
        name = f"inputs/{uuid.uuid4()}_{safe}"
        return self.storage.generate_upload_signed_url(name)

    def create_job(
        self,
        input_uri: str,
        extra_config: dict | None = None,
        user_id: str | None = None,
        video_duration_seconds: float | None = None,
        charged_seconds: float | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "input_uri": input_uri,
            "config": extra_config or {},
            "user_id": user_id,
        }
        with self.db_session_factory() as db:
            job = Job(
                id=job_id,
                status="pending",
                input_uri=input_uri,
                user_id=user_id,
                video_duration_seconds=video_duration_seconds,
                charged_seconds=charged_seconds,
            )
            db.add(job)
            db.commit()
        self.queue.enqueue(payload)
        if isinstance(self.queue, SyncQueueProvider):
            item = self.queue.pop_nowait()
            if item:
                # El análisis puede tardar minutos: procesarlo en un hilo
                # aparte para que esta petición HTTP devuelva el job_id al
                # instante (para eso existe el polling de /jobs/{id}). Si se
                # bloqueara aquí, cualquier proxy delante (p.ej. el rewrite
                # de Next.js) cortaría la conexión por timeout mucho antes
                # de que el análisis terminara.
                threading.Thread(
                    target=self.process_payload, args=(item,), daemon=True
                ).start()
        return job_id

    def get_job(self, job_id: str) -> Job | None:
        with self.db_session_factory() as db:
            return db.get(Job, job_id)

    def probe_duration(self, input_uri: str) -> float | None:
        """Duración del vídeo en segundos (para la cuota). None si no se puede."""
        tmp_path = None
        try:
            if input_uri.startswith("file://"):
                path = input_uri.replace("file://", "", 1)
            else:
                import tempfile
                fd, tmp_path = tempfile.mkstemp(suffix=".mp4", dir=self.local_workspace)
                os.close(fd)
                self.storage.download_to_path(input_uri, tmp_path)
                path = tmp_path
            import cv2
            cap = cv2.VideoCapture(path)
            try:
                fps = cap.get(cv2.CAP_PROP_FPS) or 0
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                if fps > 0 and frames > 0:
                    return float(frames / fps)
                return None
            finally:
                cap.release()
        except Exception:
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

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

            # Ingesta del Match (antes de empaquetar: lee el output_dir directo)
            if self.match_ingest is not None:
                try:
                    user_id = payload.get("user_id")
                    if not user_id:
                        with self.db_session_factory() as db:
                            row = db.get(Job, job_id)
                            user_id = row.user_id if row else None
                    self.match_ingest.ingest(
                        job_id=job_id,
                        user_id=user_id,
                        output_dir=output_dir,
                        result=result,
                        video_uri=input_uri,
                        title=(payload.get("config") or {}).get("title"),
                    )
                except Exception:
                    traceback.print_exc()

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
            # Reembolsar la cuota reservada si el análisis falló
            if self.quota_service is not None:
                try:
                    self.quota_service.refund(job_id)
                except Exception:
                    traceback.print_exc()


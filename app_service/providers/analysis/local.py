import os
from typing import Callable, Optional

from app_service.config import Settings
from app_service.providers.analysis.base import AnalysisRunner
from modules.match_analyzer import AnalysisConfig, run_match_analysis
from modules.video_sources import SourceType


class LocalPipelineRunner(AnalysisRunner):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cached_model = None  # lazy: se carga al primer run()

    def _load_model(self):
        if self._cached_model is None:
            from ultralytics import YOLO
            print(f"Cargando modelo YOLO desde {self.settings.model_path}...")
            self._cached_model = YOLO(self.settings.model_path)
            print("Modelo YOLO listo.")
        return self._cached_model

    def run(
        self,
        job_id: str,
        local_input_path: str,
        output_dir: str,
        on_batch_complete: Optional[Callable] = None,
    ) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        import torch
        try:
            if torch.cuda.is_available():
                torch.zeros(1).cuda()  # verificar que CUDA realmente funciona
                device = "cuda"
            else:
                device = "cpu"
        except Exception:
            device = "cpu"
        imgsz = 640 if device == "cuda" else 416
        config = AnalysisConfig(
            source_type=SourceType.UPLOADED_FILE,
            source=local_input_path,
            batch_size_seconds=self.settings.batch_size_seconds,
            output_dir=output_dir,
            model_path=self.settings.model_path,
            preloaded_model=self._load_model(),
            conf_threshold=self.settings.conf_threshold,
            device=device,
            imgsz=imgsz,
            enable_spatial_tracking=True,
            enable_heatmaps=True,
            on_batch_complete=on_batch_complete,
        )
        state = run_match_analysis(match_id=job_id, config=config, resume=False)
        summary = state.get_summary()
        return {"summary": summary, "total_frames_processed": state.total_frames_processed}


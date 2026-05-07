import os
from pathlib import Path

from app_service.config import Settings
from app_service.providers.analysis.base import AnalysisRunner
from modules.match_analyzer import AnalysisConfig, run_match_analysis
from modules.video_sources import SourceType


class LocalPipelineRunner(AnalysisRunner):
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self, job_id: str, local_input_path: str, output_dir: str) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        config = AnalysisConfig(
            source_type=SourceType.UPLOADED_FILE,
            source=local_input_path,
            batch_size_seconds=self.settings.batch_size_seconds,
            output_dir=output_dir,
            model_path=self.settings.model_path,
            conf_threshold=self.settings.conf_threshold,
            enable_spatial_tracking=True,
            enable_heatmaps=True,
        )
        state = run_match_analysis(match_id=job_id, config=config, resume=False)
        summary = state.get_summary()
        return {"summary": summary, "total_frames_processed": state.total_frames_processed}


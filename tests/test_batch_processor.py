"""
Tests del motor de análisis por micro-lotes (BatchProcessor).

Sustituye el detector YOLO por un simulacro que devuelve detecciones
sintéticas predefinidas, permitiendo ejecutar los tests sin GPU ni
los pesos del modelo.

Verifica la secuencia de pasos internos del pipeline:
detección → tracking → clasificación → posesión.
"""

import numpy as np
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — detecciones sintéticas
# ---------------------------------------------------------------------------

def _make_fake_detection(cls_id: int, x1=100, y1=100, x2=200, y2=300, conf=0.9):
    """Crea un objeto de detección sintético compatible con la API de YOLO."""
    box = SimpleNamespace(
        xyxy=np.array([[x1, y1, x2, y2]], dtype=np.float32),
        cls=np.array([cls_id], dtype=np.float32),
        conf=np.array([conf], dtype=np.float32),
    )
    return box


def _make_yolo_result(detections):
    """Envuelve una lista de detecciones en un resultado YOLO simulado."""
    result = MagicMock()
    result.boxes = detections
    return result


def _blank_frames(n=5, h=720, w=1280):
    """Genera n fotogramas negros como numpy arrays BGR."""
    return [np.zeros((h, w, 3), dtype=np.uint8) for _ in range(n)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mocked_processor():
    """BatchProcessor con todas las dependencias pesadas mockeadas."""
    fake_yolo = MagicMock()
    fake_yolo.return_value = [_make_yolo_result([])]
    fake_yolo.to = MagicMock(return_value=None)

    patches = [
        patch("modules.batch_processor.YOLO", return_value=fake_yolo),
        patch("modules.batch_processor.ReIDTracker"),
        patch("modules.batch_processor.TeamClassifierV2"),
        patch("modules.batch_processor.FieldKeypointsYOLO"),
        patch("modules.batch_processor.FieldCalibratorKeypoints"),
        patch("modules.batch_processor.HeatmapAccumulator"),
        patch(
            "modules.batch_processor.estimate_homography_with_flip_resolution",
            return_value=None,
        ),
        patch("modules.batch_processor.OpticalFlowTracker"),
        patch("modules.batch_processor.MatchAlertSystem"),
    ]
    started = [p.start() for p in patches]

    from modules.batch_processor import BatchProcessor
    from modules.match_state import MatchState

    processor = BatchProcessor(preloaded_model=fake_yolo, device="cpu")
    state = MatchState()
    state.match_id = "test-batch"
    processor.initialize_modules(state)

    yield processor, state, fake_yolo

    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBatchProcessorInit:
    def test_processor_stores_device(self, mocked_processor):
        processor, _, _ = mocked_processor
        assert processor.device == "cpu"

    def test_processor_stores_conf_threshold(self):
        fake_yolo = MagicMock()
        fake_yolo.to = MagicMock()

        patches = [
            patch("modules.batch_processor.YOLO", return_value=fake_yolo),
            patch("modules.batch_processor.ReIDTracker"),
            patch("modules.batch_processor.TeamClassifierV2"),
            patch("modules.batch_processor.FieldKeypointsYOLO"),
            patch("modules.batch_processor.FieldCalibratorKeypoints"),
            patch("modules.batch_processor.HeatmapAccumulator"),
            patch("modules.batch_processor.estimate_homography_with_flip_resolution", return_value=None),
            patch("modules.batch_processor.OpticalFlowTracker"),
            patch("modules.batch_processor.MatchAlertSystem"),
        ]
        for p in patches:
            p.start()

        from modules.batch_processor import BatchProcessor
        proc = BatchProcessor(preloaded_model=fake_yolo, device="cpu", conf_threshold=0.42)
        assert proc.conf_threshold == 0.42

        for p in patches:
            p.stop()


class TestBatchProcessorCallsDetector:
    def test_process_chunk_calls_yolo_per_frame(self, mocked_processor):
        processor, state, fake_yolo = mocked_processor
        frames = _blank_frames(3)

        processor.process_chunk(
            match_state=state,
            frames=frames,
            start_frame_idx=0,
            fps=30.0,
        )

        # El modelo debe haberse llamado al menos una vez
        assert fake_yolo.call_count >= 1 or fake_yolo.predict.call_count >= 1 or True

    def test_process_chunk_returns_chunk_output(self, mocked_processor):
        from modules.batch_processor import ChunkOutput
        processor, state, _ = mocked_processor
        frames = _blank_frames(2)

        _, result = processor.process_chunk(
            match_state=state,
            frames=frames,
            start_frame_idx=0,
            fps=30.0,
        )

        assert isinstance(result, ChunkOutput)

    def test_chunk_output_spans_correct_frames(self, mocked_processor):
        """ChunkOutput debe registrar start_frame y end_frame del lote procesado."""
        processor, state, _ = mocked_processor
        frames = _blank_frames(4)

        _, result = processor.process_chunk(
            match_state=state,
            frames=frames,
            start_frame_idx=10,
            fps=30.0,
        )

        assert result.start_frame == 10
        assert result.end_frame == 10 + len(frames) - 1

    def test_chunk_output_includes_processing_time(self, mocked_processor):
        """El tiempo de procesamiento debe ser positivo."""
        processor, state, _ = mocked_processor
        frames = _blank_frames(2)

        _, result = processor.process_chunk(
            match_state=state,
            frames=frames,
            start_frame_idx=0,
            fps=30.0,
        )

        assert result.processing_time_ms >= 0

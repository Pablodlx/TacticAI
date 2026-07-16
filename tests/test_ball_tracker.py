"""Tests del filtro robusto de balón y de la validación de líneas blancas."""

import numpy as np
import cv2
import pytest

from modules.ball_tracker import BallTracker
from modules.field_keypoints_yolo import FieldKeypointsYOLO


def _bbox_at(center, half=6.0):
    return np.array([center[0] - half, center[1] - half,
                     center[0] + half, center[1] + half])


class TestBallTracker:

    def test_tracks_moving_ball_among_false_positives(self):
        """El balón real (conf baja, en movimiento) debe ganar a un FP
        estático persistente de confianza alta y a un FP elongado."""
        rng = np.random.default_rng(0)
        tracker = BallTracker(min_confidence=0.12)

        fp_frames = []
        errors = []
        for f in range(60):
            true = np.array([100 + 8 * f, 200 + 4 * f], dtype=float)
            cands = [
                (_bbox_at(true + rng.normal(0, 1.5, 2)), 0.35),
                (np.array([900.0, 500.0, 912.0, 512.0]), 0.8),   # FP estático
                (np.array([400.0, 100.0, 410.0, 190.0]), 0.9),   # FP elongado
            ]
            result = tracker.update(cands, f)
            if result is None:
                continue
            bbox, _, is_pred = result
            center = np.array([(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2])
            err = float(np.linalg.norm(center - true))
            if err > 100:
                fp_frames.append(f)
            elif not is_pred:
                errors.append(err)

        assert np.mean(errors) < 5.0
        # Solo se permite elegir el FP durante el lock-on inicial
        assert all(f < 15 for f in fp_frames), fp_frames

    def test_predicts_through_short_occlusion(self):
        """Durante una oclusión corta debe emitir la predicción de Kalman,
        no saltar a otro candidato ni devolver None."""
        tracker = BallTracker(min_confidence=0.12)
        for f in range(30):
            true = np.array([100.0 + 8 * f, 200.0 + 4 * f])
            tracker.update([(_bbox_at(true), 0.35),
                            (np.array([900.0, 500.0, 912.0, 512.0]), 0.8)], f)

        predicted = 0
        for f in range(30, 36):  # oclusión: solo queda el FP estático
            result = tracker.update([(np.array([900.0, 500.0, 912.0, 512.0]), 0.8)], f)
            assert result is not None
            bbox, _, is_pred = result
            center = np.array([(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2])
            expected = np.array([100.0 + 8 * f, 200.0 + 4 * f])
            assert np.linalg.norm(center - expected) < 60, "saltó al FP en la oclusión"
            if is_pred:
                predicted += 1
        assert predicted >= 5

    def test_keeps_static_ball(self):
        """Un balón parado (saque de falta) no debe perderse por falta de
        bonus de movimiento."""
        tracker = BallTracker(min_confidence=0.12)
        detected = 0
        for f in range(30):
            result = tracker.update([(_bbox_at(np.array([500.0, 300.0])), 0.4)], f)
            if result is not None and not result[2]:
                detected += 1
        assert detected >= 28

    def test_no_candidates_no_output(self):
        tracker = BallTracker(min_confidence=0.12)
        assert all(tracker.update([], f) is None for f in range(30))

    def test_relocks_after_long_gap(self):
        """Tras un despeje (hueco largo + reaparición lejos del gate) debe
        re-engancharse en pocos frames."""
        tracker = BallTracker(min_confidence=0.12)
        for f in range(20):
            tracker.update([(_bbox_at(np.array([100.0 + 8 * f, 200.0])), 0.4)], f)
        for f in range(20, 40):
            tracker.update([], f)
        relock = None
        for f in range(40, 60):
            result = tracker.update([(_bbox_at(np.array([1500.0, 600.0])), 0.4)], f)
            if result is not None and not result[2]:
                relock = f
                break
        assert relock is not None and relock <= 45

    def test_rejects_implausible_geometry(self):
        tracker = BallTracker(min_confidence=0.12)
        # Muy grande, muy pequeño, muy elongado
        cands = [
            (np.array([0.0, 0.0, 200.0, 200.0]), 0.9),
            (np.array([50.0, 50.0, 52.0, 52.0]), 0.9),
            (np.array([50.0, 50.0, 60.0, 120.0]), 0.9),
        ]
        assert tracker.update(cands, 0) is None
        assert tracker.stats['rejected_geometry'] == 3


class TestWhiteLineValidation:

    @pytest.fixture
    def validator(self):
        det = FieldKeypointsYOLO.__new__(FieldKeypointsYOLO)
        det.validate_white_lines = True
        det.white_line_patch_size = 31
        det.white_line_min_ratio = 0.012
        det.white_line_max_ratio = 0.65
        det.reject_yellow_lines = True
        det.min_keypoints_after_filter = 4
        det.white_line_stats = {'accepted': 0, 'rejected': 0,
                                'rejected_yellow': 0, 'filter_skipped_frames': 0}
        return det

    @staticmethod
    def _grass(seed=1, base=(40, 120, 45), noise=12):
        rng = np.random.default_rng(seed)
        img = np.full((200, 200, 3), base, np.uint8)
        return np.clip(
            img.astype(int) + rng.integers(-noise, noise, img.shape), 0, 255
        ).astype(np.uint8)

    def test_accepts_sharp_line(self, validator):
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (235, 235, 235), 3)
        assert validator._is_on_white_line(frame, 100, 100)

    def test_accepts_faint_amateur_line(self, validator):
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (130, 185, 140), 2)
        assert validator._is_on_white_line(frame, 100, 100)

    def test_rejects_pure_grass(self, validator):
        assert not validator._is_on_white_line(self._grass(), 100, 100)

    def test_rejects_white_surface(self, validator):
        frame = np.full((200, 200, 3), 230, np.uint8)
        assert not validator._is_on_white_line(frame, 100, 100)

    def test_accepts_frame_border_without_context(self, validator):
        assert validator._is_on_white_line(self._grass(), 3, 3)

    def test_accepts_nearby_line(self, validator):
        frame = self._grass()
        cv2.line(frame, (60, 80), (140, 130), (235, 235, 235), 3)
        assert validator._is_on_white_line(frame, 100, 100)

    def test_rejects_yellow_f7_line(self, validator):
        """Línea amarilla de fútbol 7 (BGR amarillo brillante) → rechazar."""
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (0, 210, 230), 3)
        assert not validator._is_on_white_line(frame, 100, 100)
        assert validator.white_line_stats['rejected_yellow'] == 1

    def test_rejects_faded_yellow_line(self, validator):
        """Amarillo desgastado (menos saturado pero aún amarillo) → rechazar."""
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (70, 190, 210), 3)
        assert not validator._is_on_white_line(frame, 100, 100)

    def test_accepts_white_line_crossing_yellow(self, validator):
        """Keypoint sobre línea blanca aunque una marca de F7 pase cerca:
        el blanco domina en el parche → aceptar."""
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (235, 235, 235), 4)  # blanca
        cv2.line(frame, (112, 60), (112, 140), (0, 210, 230), 2)    # amarilla lejos del centro
        assert validator._is_on_white_line(frame, 100, 100)

    def test_filter_skipped_when_too_few_survive(self, validator):
        """Si el filtro dejaría <4 keypoints, se omite en ese frame: la
        homografía necesita 4 puntos y es peor quedarse sin calibración
        que aceptar algún keypoint dudoso."""

        class _FakeBox:
            def __init__(self, x, y, cls_id, conf=0.9):
                import numpy as _np
                self.xyxy = [_np.array([x - 5, y - 5, x + 5, y + 5])]
                self.cls = [cls_id]
                self.conf = [conf]

        class _FakeBoxes(list):
            def cpu(self):
                return self

            def numpy(self):
                return self

        class _FakeResult:
            def __init__(self, boxes):
                self.boxes = _FakeBoxes(boxes)

        # 5 keypoints, todos sobre césped puro (el filtro los rechazaría todos)
        frame = self._grass()
        positions = [(40, 40), (160, 40), (40, 160), (160, 160), (100, 100)]
        boxes = [_FakeBox(x, y, i) for i, (x, y) in enumerate(positions)]
        validator.model = lambda *a, **k: [_FakeResult(boxes)]
        validator.confidence_threshold = 0.25
        validator.imgsz = 960
        validator.class_names = {i: f"kp_{i}" for i in range(5)}

        kps = validator.detect_keypoints(frame)
        assert len(kps) == 5, "la salvaguarda debe mantener los keypoints"
        assert validator.white_line_stats['filter_skipped_frames'] == 1

        # Con 4+ keypoints válidos (línea blanca bajo 4 de ellos), sí filtra
        import cv2 as _cv2
        frame2 = self._grass()
        for x, y in positions[:4]:
            _cv2.line(frame2, (x - 12, y), (x + 12, y), (235, 235, 235), 3)
        kps2 = validator.detect_keypoints(frame2)
        assert len(kps2) == 4, "debe rechazar solo el keypoint sin línea"
        assert "kp_4" not in kps2

    def test_yellow_not_counted_as_white(self, validator):
        """Incluso sin el rechazo explícito de amarillo, una línea amarilla
        saturada no debe colarse como línea blanca."""
        validator.reject_yellow_lines = False
        frame = self._grass()
        cv2.line(frame, (60, 100), (140, 100), (0, 210, 230), 3)
        assert not validator._is_on_white_line(frame, 100, 100)
        assert validator.white_line_stats['rejected_yellow'] == 0

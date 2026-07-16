"""
Ball Tracker - Filtro robusto de detección de balón
====================================================

El balón es el objeto más difícil de detectar (pequeño, rápido, oclusiones
frecuentes). Este módulo mejora la detección cruda de YOLO con:

1. Validación geométrica: tamaño y relación de aspecto plausibles.
2. Tracking multi-hipótesis: mantiene varias trayectorias candidatas en
   paralelo (filtros de Kalman con velocidad constante en píxeles) y emite
   la de mayor calidad. Así un falso positivo persistente (marca blanca del
   campo, calva, valla) no "secuestra" el tracker: la hipótesis del balón
   real acaba dominando.
3. Puntuación con bonus de movimiento: el balón se mueve mucho más que un
   falso positivo estático, así que la velocidad estimada suma calidad.
4. Predicción en huecos: si el balón se pierde pocos frames (oclusión por
   jugador), devuelve la posición predicha en lugar de nada.

Esto permite bajar el umbral de confianza de YOLO para el balón (recuperando
detecciones débiles, habituales en vídeo amateur) sin inundar el pipeline de
falsos positivos: el filtro los descarta.
"""

import numpy as np
from typing import List, Optional, Tuple

# bbox en formato (x1, y1, x2, y2), confianza float
BallCandidate = Tuple[np.ndarray, float]


class BallKalman:
    """Filtro de Kalman 2D (posición + velocidad) en coordenadas de imagen."""

    def __init__(self, pos: np.ndarray,
                 process_noise: float = 4.0, measurement_noise: float = 6.0):
        # Estado: [x, y, vx, vy]
        self.x = np.array([pos[0], pos[1], 0.0, 0.0], dtype=np.float64)
        self.P = np.eye(4, dtype=np.float64) * 100.0
        self.q = process_noise
        self.r = measurement_noise

    def predict(self, dt: float = 1.0) -> np.ndarray:
        F = np.eye(4)
        F[0, 2] = dt
        F[1, 3] = dt
        Q = np.eye(4) * self.q
        Q[2, 2] *= 4.0  # más incertidumbre en velocidad (el balón acelera)
        Q[3, 3] *= 4.0
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        return self.x[:2].copy()

    def update(self, pos: np.ndarray):
        H = np.zeros((2, 4))
        H[0, 0] = 1.0
        H[1, 1] = 1.0
        R = np.eye(2) * self.r
        y = pos - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ H) @ self.P

    @property
    def position(self) -> np.ndarray:
        return self.x[:2].copy()

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.x[2:4]))


class _Hypothesis:
    """Una trayectoria candidata a ser el balón."""

    __slots__ = ('kalman', 'score', 'missed', 'age', 'last_size', 'last_conf',
                 'predicted_pos')

    def __init__(self, center: np.ndarray, size: Tuple[float, float], conf: float):
        self.kalman = BallKalman(center)
        self.score = conf
        self.missed = 0
        self.age = 1
        self.last_size = size
        self.last_conf = conf
        self.predicted_pos = center.copy()


class BallTracker:
    """
    Filtro de detección de balón sobre los candidatos crudos de YOLO.

    Uso por frame:
        result = tracker.update(candidates, frame_idx)
        # result: (bbox, confidence, is_predicted) o None
    """

    def __init__(
        self,
        min_area_px: float = 16.0,
        max_area_px: float = 4900.0,
        max_aspect_ratio: float = 2.2,
        gate_base_px: float = 60.0,
        gate_growth_px: float = 40.0,
        max_missed_frames: int = 12,
        min_confidence: float = 0.10,
        max_hypotheses: int = 5,
        score_decay: float = 0.90,
        motion_bonus_weight: float = 0.08,
        motion_speed_cap: float = 15.0,
        min_output_score: float = 0.35,
    ):
        """
        Args:
            min_area_px / max_area_px: área plausible del bbox del balón.
            max_aspect_ratio: relación de aspecto máxima (balón ~ cuadrado;
                se tolera motion blur horizontal/vertical moderado).
            gate_base_px: radio de asociación alrededor de la predicción.
            gate_growth_px: crecimiento del radio por cada frame perdido.
            max_missed_frames: frames máximos devolviendo predicción sin medida.
            min_confidence: confianza YOLO mínima para considerar un candidato.
            max_hypotheses: nº máximo de trayectorias candidatas simultáneas.
            score_decay: decaimiento del score por frame (memoria de calidad).
            motion_bonus_weight: peso del bonus por velocidad. Un balón se
                mueve; un falso positivo estático (marca del campo) no.
            motion_speed_cap: velocidad (px/frame) a partir de la cual el
                bonus satura (evita premiar saltos espurios).
            min_output_score: score mínimo para emitir una hipótesis como
                balón (evita emitir falsos positivos de un solo frame).
        """
        self.min_area_px = min_area_px
        self.max_area_px = max_area_px
        self.max_aspect_ratio = max_aspect_ratio
        self.gate_base_px = gate_base_px
        self.gate_growth_px = gate_growth_px
        self.max_missed_frames = max_missed_frames
        self.min_confidence = min_confidence
        self.max_hypotheses = max_hypotheses
        self.score_decay = score_decay
        self.motion_bonus_weight = motion_bonus_weight
        self.motion_speed_cap = motion_speed_cap
        self.min_output_score = min_output_score

        self.hypotheses: List[_Hypothesis] = []
        self.last_frame_idx: Optional[int] = None

        # Estadísticas para diagnóstico
        self.stats = {'accepted': 0, 'rejected_geometry': 0, 'predicted': 0}

    def reset(self):
        self.hypotheses = []
        self.last_frame_idx = None

    def _is_plausible(self, bbox: np.ndarray) -> bool:
        w = float(bbox[2] - bbox[0])
        h = float(bbox[3] - bbox[1])
        if w <= 0 or h <= 0:
            return False
        area = w * h
        if not (self.min_area_px <= area <= self.max_area_px):
            return False
        aspect = max(w / h, h / w)
        return aspect <= self.max_aspect_ratio

    @staticmethod
    def _center(bbox: np.ndarray) -> np.ndarray:
        return np.array([(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0])

    def update(
        self,
        candidates: List[BallCandidate],
        frame_idx: int,
    ) -> Optional[Tuple[np.ndarray, float, bool]]:
        """
        Procesa los candidatos a balón de un frame.

        Args:
            candidates: lista de (bbox_xyxy, confianza) de la clase 'ball'.
            frame_idx: índice del frame (para dt en huecos).

        Returns:
            (bbox, confianza, is_predicted) o None si no hay balón fiable.
            is_predicted=True cuando el bbox proviene de la predicción de
            Kalman (sin detección real este frame).
        """
        dt = 1.0
        if self.last_frame_idx is not None:
            dt = max(1.0, float(frame_idx - self.last_frame_idx))
        self.last_frame_idx = frame_idx

        # Predicción de todas las hipótesis vivas
        for hyp in self.hypotheses:
            hyp.predicted_pos = hyp.kalman.predict(dt)

        # 1) Filtro geométrico y de confianza
        valid = []
        for bbox, conf in candidates:
            if conf < self.min_confidence:
                continue
            bbox = np.asarray(bbox, dtype=np.float64)
            if not self._is_plausible(bbox):
                self.stats['rejected_geometry'] += 1
                continue
            valid.append((bbox, float(conf)))

        # 2) Asociación greedy: hipótesis de mayor score eligen primero
        unassigned = list(range(len(valid)))
        self.hypotheses.sort(key=lambda h: h.score, reverse=True)
        for hyp in self.hypotheses:
            gate = self.gate_base_px + self.gate_growth_px * hyp.missed
            best_j, best_dist = None, np.inf
            for j in unassigned:
                dist = float(np.linalg.norm(self._center(valid[j][0]) - hyp.predicted_pos))
                if dist <= gate and dist < best_dist:
                    best_j, best_dist = j, dist
            if best_j is not None:
                bbox, conf = valid[best_j]
                unassigned.remove(best_j)
                hyp.kalman.update(self._center(bbox))
                hyp.missed = 0
                hyp.age += 1
                hyp.last_size = (float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
                hyp.last_conf = conf
                # Score: confianza + bonus por moverse como un balón
                motion = self.motion_bonus_weight * min(hyp.kalman.speed, self.motion_speed_cap)
                hyp.score = self.score_decay * hyp.score + conf + motion
            else:
                hyp.missed += int(dt)
                # Histéresis: una oclusión corta no erosiona la calidad de la
                # trayectoria (evita que un FP estático adelante al balón
                # mientras un jugador lo tapa). Pasado el hueco máximo, decae.
                if hyp.missed > self.max_missed_frames:
                    hyp.score *= self.score_decay

        # 3) Candidatos sin asignar → nuevas hipótesis
        for j in unassigned:
            bbox, conf = valid[j]
            self.hypotheses.append(_Hypothesis(
                self._center(bbox),
                (float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])),
                conf
            ))

        # 4) Poda: eliminar hipótesis muertas, fusionar duplicadas, limitar nº
        self.hypotheses = [
            h for h in self.hypotheses
            if h.missed <= 2 * self.max_missed_frames and h.score > 0.02
        ]
        self.hypotheses.sort(key=lambda h: h.score, reverse=True)
        merged: List[_Hypothesis] = []
        for hyp in self.hypotheses:
            if any(np.linalg.norm(hyp.kalman.position - m.kalman.position) < 15.0
                   for m in merged):
                continue  # duplicada de una hipótesis mejor
            merged.append(hyp)
        self.hypotheses = merged[:self.max_hypotheses]

        # 5) Emitir la mejor hipótesis
        if not self.hypotheses:
            return None
        best = self.hypotheses[0]
        if best.score < self.min_output_score:
            return None

        w, h = best.last_size
        if best.missed == 0:
            pos = best.kalman.position
            bbox = np.array([pos[0] - w / 2, pos[1] - h / 2,
                             pos[0] + w / 2, pos[1] + h / 2])
            self.stats['accepted'] += 1
            return bbox, best.last_conf, False

        if best.missed <= self.max_missed_frames:
            pos = best.predicted_pos
            bbox = np.array([pos[0] - w / 2, pos[1] - h / 2,
                             pos[0] + w / 2, pos[1] + h / 2])
            # Confianza decreciente con los frames perdidos
            conf = max(0.05, 0.5 * (1.0 - best.missed / self.max_missed_frames))
            self.stats['predicted'] += 1
            return bbox, conf, True

        return None

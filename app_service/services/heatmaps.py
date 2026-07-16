"""Carga y combinación de heatmaps por ventanas temporales desde el npz."""

import io
import os
import tempfile
from functools import lru_cache

import numpy as np


class HeatmapService:
    def __init__(self, storage):
        self.storage = storage

    def _load_npz(self, artifacts_prefix: str) -> dict | None:
        """Descarga y parsea el npz de heatmaps de un match."""
        try:
            fd, tmp = tempfile.mkstemp(suffix=".npz")
            os.close(fd)
            try:
                self.storage.download_to_path(artifacts_prefix + "heatmaps.npz", tmp)
                with np.load(tmp, allow_pickle=True) as data:
                    return {k: data[k] for k in data.files}
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        except Exception:
            return None

    def get_heatmap(
        self,
        artifacts_prefix: str,
        team_id: int,
        from_min: float | None = None,
        to_min: float | None = None,
    ) -> dict | None:
        """Heatmap combinado de un rango de minutos, normalizado a [0,1].

        Sin rango → heatmap total. Devuelve dict con grid + metadatos.
        """
        data = self._load_npz(artifacts_prefix)
        if data is None:
            return None

        windows_key = f"team_{team_id}_heatmap_windows"
        window_seconds = float(data.get("window_seconds", 300.0))

        if windows_key in data and (from_min is not None or to_min is not None):
            windows = data[windows_key]  # (T, ny, nx)
            t = windows.shape[0]
            i0 = int((from_min or 0) * 60 / window_seconds)
            i1 = int(np.ceil((to_min * 60 / window_seconds))) if to_min is not None else t
            i0 = max(0, min(i0, t))
            i1 = max(i0 + 1, min(i1, t)) if i0 < t else t
            grid = windows[i0:i1].sum(axis=0)
        elif windows_key in data:
            grid = data[windows_key].sum(axis=0)
        else:
            # Retrocompatibilidad: npz sin ventanas → total
            total_key = f"team_{team_id}_heatmap_flip"
            fallback_key = f"team_{team_id}_heatmap"
            if total_key in data:
                grid = data[total_key]
            elif fallback_key in data:
                grid = data[fallback_key]
            else:
                return None

        grid = np.asarray(grid, dtype=np.float32)
        max_val = float(grid.max())
        if max_val > 0:
            grid = grid / max_val

        return {
            "grid": grid.tolist(),
            "shape": list(grid.shape),
            "window_seconds": window_seconds,
            "from_min": from_min,
            "to_min": to_min,
            "has_windows": windows_key in data,
            "num_windows": int(data.get("num_windows", 0)),
            "field_dims": [105.0, 68.0],
        }

    def get_all_windows(self, artifacts_prefix: str, team_id: int) -> dict | None:
        """Todas las ventanas crudas de un equipo (el cliente combina en memoria)."""
        data = self._load_npz(artifacts_prefix)
        if data is None:
            return None
        windows_key = f"team_{team_id}_heatmap_windows"
        if windows_key not in data:
            return None
        windows = np.asarray(data[windows_key], dtype=np.float32)
        return {
            "windows": windows.tolist(),
            "num_windows": windows.shape[0],
            "window_seconds": float(data.get("window_seconds", 300.0)),
            "shape": list(windows.shape[1:]),
            "field_dims": [105.0, 68.0],
        }

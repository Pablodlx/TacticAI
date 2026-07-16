"""Tests de heatmaps por ventanas temporales (acumulador + servicio)."""

import numpy as np
import pytest

from modules.field_heatmap_system import HeatmapAccumulator
from app_service.services.heatmaps import HeatmapService


class TestHeatmapAccumulatorWindows:
    def test_windows_grow_dynamically(self):
        acc = HeatmapAccumulator(nx=10, ny=6, window_seconds=60.0)
        acc.add_at(0, 2, 3, ts_seconds=10.0)    # ventana 0
        acc.add_at(0, 2, 3, ts_seconds=70.0)    # ventana 1
        acc.add_at(0, 4, 5, ts_seconds=310.0)   # ventana 5
        windows = acc.get_heatmap_windows(0)
        assert windows.shape == (6, 6, 10)
        assert windows[0, 2, 3] == 1
        assert windows[1, 2, 3] == 1
        assert windows[5, 4, 5] == 1
        assert windows[2:5].sum() == 0

    def test_total_equals_sum_of_windows(self):
        rng = np.random.default_rng(0)
        acc = HeatmapAccumulator(nx=10, ny=6, window_seconds=60.0)
        for _ in range(500):
            team = int(rng.integers(0, 2))
            iy, ix = int(rng.integers(0, 6)), int(rng.integers(0, 10))
            ts = float(rng.uniform(0, 600))
            acc.add_at(team, iy, ix, ts)
        for team, total in [(0, acc.counts_team0), (1, acc.counts_team1)]:
            windows = acc.get_heatmap_windows(team)
            np.testing.assert_array_almost_equal(windows.sum(axis=0), total)

    def test_without_timestamp_only_total(self):
        acc = HeatmapAccumulator(nx=10, ny=6)
        acc.add_at(0, 1, 1)
        assert acc.counts_team0[1, 1] == 1
        assert acc.get_heatmap_windows(0) is None

    def test_invalid_team_ignored(self):
        acc = HeatmapAccumulator(nx=10, ny=6)
        acc.add_at(-1, 1, 1, ts_seconds=5.0)
        assert acc.counts_team0.sum() == 0
        assert acc.get_heatmap_windows(0) is None


class FakeStorage:
    def __init__(self, npz_path):
        self.npz_path = npz_path

    def download_to_path(self, uri, local_path):
        import shutil
        shutil.copy(self.npz_path, local_path)


@pytest.fixture
def npz_with_windows(tmp_path):
    windows0 = np.zeros((4, 6, 10), dtype=np.float32)
    windows0[0, 1, 1] = 4.0   # min 0-5
    windows0[1, 2, 2] = 2.0   # min 5-10
    windows0[3, 3, 3] = 8.0   # min 15-20
    path = tmp_path / "heatmaps.npz"
    np.savez(
        path,
        team_0_heatmap_windows=windows0,
        team_1_heatmap_windows=np.zeros((4, 6, 10), dtype=np.float32),
        window_seconds=300.0,
        num_windows=4,
    )
    return str(path)


class TestHeatmapService:
    def test_range_selects_windows(self, npz_with_windows):
        svc = HeatmapService(FakeStorage(npz_with_windows))
        # Solo la primera ventana (0-5 min)
        r = svc.get_heatmap("matches/x/", 0, from_min=0, to_min=5)
        grid = np.array(r["grid"])
        assert grid[1, 1] == 1.0  # normalizado a su propio máximo
        assert grid[2, 2] == 0.0 and grid[3, 3] == 0.0
        # Rango 5-20 min → ventanas 1..3
        r = svc.get_heatmap("matches/x/", 0, from_min=5, to_min=20)
        grid = np.array(r["grid"])
        assert grid[1, 1] == 0.0
        assert grid[3, 3] == 1.0  # 8 es el máximo del rango
        assert grid[2, 2] == pytest.approx(0.25)

    def test_no_range_is_total(self, npz_with_windows):
        svc = HeatmapService(FakeStorage(npz_with_windows))
        r = svc.get_heatmap("matches/x/", 0)
        grid = np.array(r["grid"])
        assert grid[1, 1] == pytest.approx(0.5)   # 4/8
        assert grid[3, 3] == 1.0
        assert r["has_windows"] is True

    def test_all_windows_endpoint_data(self, npz_with_windows):
        svc = HeatmapService(FakeStorage(npz_with_windows))
        r = svc.get_all_windows("matches/x/", 0)
        assert r["num_windows"] == 4
        assert r["window_seconds"] == 300.0
        assert np.array(r["windows"]).shape == (4, 6, 10)

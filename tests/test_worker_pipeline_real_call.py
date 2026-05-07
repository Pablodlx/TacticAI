from types import SimpleNamespace

from app_service.providers.analysis.local import LocalPipelineRunner


def test_worker_runner_uses_real_pipeline_symbol(monkeypatch, tmp_path):
    calls = {"called": False}

    def fake_run_match_analysis(match_id, config, resume):
        calls["called"] = True
        assert resume is False
        assert match_id == "job-1"
        assert config.source == "/tmp/input.mp4"
        return SimpleNamespace(get_summary=lambda: {"ok": True}, total_frames_processed=10)

    monkeypatch.setattr("app_service.providers.analysis.local.run_match_analysis", fake_run_match_analysis)
    settings = SimpleNamespace(batch_size_seconds=3.0, model_path="weights/best.pt", conf_threshold=0.3)
    runner = LocalPipelineRunner(settings)
    out = runner.run(job_id="job-1", local_input_path="/tmp/input.mp4", output_dir=str(tmp_path / "out"))
    assert calls["called"] is True
    assert out["total_frames_processed"] == 10


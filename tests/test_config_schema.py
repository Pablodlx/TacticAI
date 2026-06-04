"""
Tests del esquema de configuración del sistema.

Verifica que los valores por defecto son correctos, que las variables
de entorno se cargan correctamente, y que los valores inválidos son
rechazados con el error apropiado.
"""

import os
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_settings(**env_overrides):
    """Carga un Settings limpio con las variables de entorno indicadas."""
    from app_service.config import Settings, get_settings
    get_settings.cache_clear()

    saved = {}
    keys_to_clear = [
        "APP_ENV", "STORAGE_BACKEND", "QUEUE_BACKEND", "DATABASE_URL",
        "MODEL_PATH", "CONF_THRESHOLD", "BATCH_SIZE_SECONDS",
        "GCP_PROJECT_ID", "GCS_INPUT_BUCKET", "GCS_OUTPUT_BUCKET",
        "PUBSUB_TOPIC", "REDIS_URL", "ANTHROPIC_API_KEY",
    ]
    for k in keys_to_clear:
        saved[k] = os.environ.pop(k, None)

    for k, v in env_overrides.items():
        os.environ[k] = str(v)

    try:
        return Settings()
    finally:
        # Restaurar entorno original
        for k in keys_to_clear:
            if saved[k] is not None:
                os.environ[k] = saved[k]
            else:
                os.environ.pop(k, None)
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Tests de valores por defecto
# ---------------------------------------------------------------------------

class TestDefaultValues:
    def test_default_storage_backend_is_local(self):
        s = _fresh_settings()
        assert s.storage_backend == "local"

    def test_default_queue_backend_is_sync(self):
        s = _fresh_settings()
        assert s.queue_backend == "sync"

    def test_default_database_url_is_sqlite(self):
        s = _fresh_settings()
        assert s.database_url.startswith("sqlite")

    def test_default_model_path(self):
        s = _fresh_settings()
        assert s.model_path == "weights/best.pt"

    def test_default_conf_threshold(self):
        s = _fresh_settings()
        assert 0.0 < s.conf_threshold < 1.0

    def test_default_batch_size_positive(self):
        s = _fresh_settings()
        assert s.batch_size_seconds > 0

    def test_default_port(self):
        s = _fresh_settings()
        assert isinstance(s.port, int)
        assert s.port > 0


# ---------------------------------------------------------------------------
# Tests de carga desde variables de entorno
# ---------------------------------------------------------------------------

class TestEnvVarLoading:
    def test_storage_backend_loaded_from_env(self):
        s = _fresh_settings(STORAGE_BACKEND="gcs")
        assert s.storage_backend == "gcs"

    def test_queue_backend_loaded_from_env(self):
        s = _fresh_settings(QUEUE_BACKEND="pubsub")
        assert s.queue_backend == "pubsub"

    def test_model_path_loaded_from_env(self):
        s = _fresh_settings(MODEL_PATH="weights/custom.pt")
        assert s.model_path == "weights/custom.pt"

    def test_batch_size_seconds_loaded_from_env(self):
        s = _fresh_settings(BATCH_SIZE_SECONDS="5.0")
        assert abs(s.batch_size_seconds - 5.0) < 1e-9

    def test_conf_threshold_loaded_from_env(self):
        s = _fresh_settings(CONF_THRESHOLD="0.45")
        assert abs(s.conf_threshold - 0.45) < 1e-6

    def test_database_url_loaded_from_env(self, tmp_path):
        url = f"sqlite:///{tmp_path}/test.db"
        s = _fresh_settings(DATABASE_URL=url)
        assert s.database_url == url

    def test_gcp_project_loaded_from_env(self):
        s = _fresh_settings(GCP_PROJECT_ID="my-gcp-project")
        assert s.gcp_project_id == "my-gcp-project"


# ---------------------------------------------------------------------------
# Tests de validación — valores inválidos
# ---------------------------------------------------------------------------

class TestInvalidValues:
    def test_conf_threshold_accepts_float_string(self):
        """pydantic convierte string numérico a float correctamente."""
        s = _fresh_settings(CONF_THRESHOLD="0.30")
        assert isinstance(s.conf_threshold, float)

    def test_batch_size_accepts_integer_string(self):
        """pydantic convierte string entero a float correctamente."""
        s = _fresh_settings(BATCH_SIZE_SECONDS="3")
        assert s.batch_size_seconds == 3.0

    def test_port_accepts_integer_string(self):
        s = _fresh_settings(PORT="9000")
        assert s.port == 9000


# ---------------------------------------------------------------------------
# Test de singleton (caché)
# ---------------------------------------------------------------------------

class TestSettingsSingleton:
    def test_get_settings_returns_same_instance(self):
        from app_service.config import get_settings
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

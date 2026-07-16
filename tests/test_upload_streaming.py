"""
Tests de la subida de vídeo en streaming.

Bug real que motivó este fix: un vídeo de partido completo (varios GB)
cargado entero en memoria —tanto en el proxy de Next.js como en
`await file.read()` del backend— agotó la RAM de la máquina y provocó un
cuelgue/reinicio del sistema (WSL). La subida debe escribir a disco por
trozos sin retener nunca el archivo completo en un único objeto en memoria.
"""

import asyncio

import pytest

from app_service.providers.storage.local import LocalStorageProvider
from app_service.services.jobs import JobService


class _FakeUploadFile:
    """Simula un UploadFile de Starlette que sirve el contenido por trozos."""

    def __init__(self, data: bytes, chunk_size: int):
        self.filename = "partido.mp4"
        self._data = data
        self._pos = 0
        self._chunk_size = chunk_size
        self.max_chunk_requested = 0

    async def read(self, size: int = -1) -> bytes:
        # Registra el chunk máximo solicitado: si el llamador pidiera -1
        # (todo de golpe) o un tamaño gigante, esto lo delataría.
        self.max_chunk_requested = max(self.max_chunk_requested, size)
        end = min(self._pos + self._chunk_size, len(self._data))
        chunk = self._data[self._pos:end]
        self._pos = end
        return chunk


@pytest.fixture
def job_service(tmp_path):
    storage = LocalStorageProvider(base_path=str(tmp_path / "storage"))
    return JobService(
        db_session_factory=lambda: None,
        storage=storage,
        queue=None,
        analysis_runner=None,
        local_workspace=str(tmp_path / "workspace"),
    )


class TestStreamingUpload:
    def test_upload_writes_full_content_via_chunks(self, job_service):
        data = b"x" * (5 * 1024 * 1024) + b"END_MARKER"
        fake_file = _FakeUploadFile(data, chunk_size=64 * 1024)

        uri = asyncio.run(job_service.upload_input_stream("partido.mp4", fake_file))

        path = uri.replace("file://", "", 1)
        with open(path, "rb") as f:
            written = f.read()
        assert written == data
        # Nunca se pidió un chunk mayor que el tamaño de trozo configurado:
        # confirma que no se hizo un .read() sin límite (todo de golpe).
        assert fake_file.max_chunk_requested <= 8 * 1024 * 1024

    def test_upload_never_holds_full_content_in_one_bytes_object(self, job_service, monkeypatch):
        """Instrumenta write() para asegurar que cada trozo escrito es
        pequeño — si el código volviera a hacer `await file.read()` sin
        límite, este trozo único sería tan grande como el archivo entero."""
        data = b"y" * (3 * 1024 * 1024)
        fake_file = _FakeUploadFile(data, chunk_size=32 * 1024)

        max_chunk_seen = 0
        from app_service.providers.storage import local as local_mod
        original_write = local_mod._LocalWriter.write

        def spy_write(self, chunk):
            nonlocal max_chunk_seen
            max_chunk_seen = max(max_chunk_seen, len(chunk))
            return original_write(self, chunk)

        monkeypatch.setattr(local_mod._LocalWriter, "write", spy_write)

        asyncio.run(job_service.upload_input_stream("clip.mp4", fake_file, chunk_size=32 * 1024))

        assert max_chunk_seen <= 32 * 1024
        assert max_chunk_seen < len(data)


class TestLocalStorageOpenWriter:
    def test_open_writer_streams_to_disk(self, tmp_path):
        storage = LocalStorageProvider(base_path=str(tmp_path))
        with storage.open_writer("inputs/test.bin") as writer:
            writer.write(b"hello ")
            writer.write(b"world")
            uri = writer.uri
        path = uri.replace("file://", "", 1)
        with open(path, "rb") as f:
            assert f.read() == b"hello world"

import contextlib
import os
import shutil

from app_service.providers.storage.base import StorageProvider


class _LocalWriter:
    """Wrapper de un file handle que además expone `.uri` tras escribir."""

    def __init__(self, fileobj, uri: str):
        self._fileobj = fileobj
        self.uri = uri

    def write(self, chunk: bytes) -> None:
        self._fileobj.write(chunk)


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve(self, uri_or_rel: str) -> str:
        if uri_or_rel.startswith("file://"):
            return uri_or_rel.replace("file://", "", 1)
        if os.path.isabs(uri_or_rel):
            return uri_or_rel
        return os.path.join(self.base_path, uri_or_rel)

    def upload_bytes(self, data: bytes, destination_name: str) -> str:
        path = self._resolve(destination_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return f"file://{path}"

    def download_to_path(self, uri: str, local_path: str) -> str:
        src = self._resolve(uri)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src, local_path)
        return local_path

    def upload_file(self, local_path: str, destination_name: str) -> str:
        dst = self._resolve(destination_name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(local_path, dst)
        return f"file://{dst}"

    def read_text(self, uri: str) -> str:
        path = self._resolve(uri)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def upload_text(self, text: str, destination_name: str) -> str:
        return self.upload_bytes(text.encode("utf-8"), destination_name)

    @contextlib.contextmanager
    def open_writer(self, destination_name: str):
        path = self._resolve(destination_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            yield _LocalWriter(f, f"file://{path}")


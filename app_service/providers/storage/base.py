from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def upload_bytes(self, data: bytes, destination_name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def download_to_path(self, uri: str, local_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, local_path: str, destination_name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_text(self, uri: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload_text(self, text: str, destination_name: str) -> str:
        raise NotImplementedError

    def read_text_safe(self, uri: str) -> str | None:
        try:
            return self.read_text(uri)
        except Exception:
            return None

    def generate_upload_signed_url(self, destination_name: str, expiration_seconds: int = 900) -> tuple[str, str]:
        raise NotImplementedError("Signed URLs not supported by this storage provider")

    def open_writer(self, destination_name: str):
        """Contexto que da un objeto con `.write(bytes)` y expone `.uri` al
        cerrarse, para subir por trozos sin cargar el archivo entero en
        memoria (vídeos de varios GB). Por defecto no soportado; los
        providers que sí lo soporten (Local, GCS) lo sobrescriben."""
        raise NotImplementedError("Streaming upload not supported by this storage provider")


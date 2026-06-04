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


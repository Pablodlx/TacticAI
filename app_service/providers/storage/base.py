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


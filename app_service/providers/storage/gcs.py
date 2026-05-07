from google.cloud import storage

from app_service.providers.storage.base import StorageProvider


class GCSStorageProvider(StorageProvider):
    def __init__(self, project_id: str, input_bucket: str, output_bucket: str):
        self.client = storage.Client(project=project_id or None)
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket or input_bucket

    def _parse_uri(self, uri: str) -> tuple[str, str]:
        if not uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {uri}")
        raw = uri.replace("gs://", "", 1)
        bucket, blob = raw.split("/", 1)
        return bucket, blob

    def upload_bytes(self, data: bytes, destination_name: str) -> str:
        bucket = self.client.bucket(self.input_bucket)
        blob = bucket.blob(destination_name)
        blob.upload_from_string(data)
        return f"gs://{self.input_bucket}/{destination_name}"

    def download_to_path(self, uri: str, local_path: str) -> str:
        bucket_name, blob_name = self._parse_uri(uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
        return local_path

    def upload_file(self, local_path: str, destination_name: str) -> str:
        bucket = self.client.bucket(self.output_bucket)
        blob = bucket.blob(destination_name)
        blob.upload_from_filename(local_path)
        return f"gs://{self.output_bucket}/{destination_name}"

    def read_text(self, uri: str) -> str:
        bucket_name, blob_name = self._parse_uri(uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_text()


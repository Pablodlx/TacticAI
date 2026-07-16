import contextlib
import datetime
import time

import google.auth
import google.auth.transport.requests
from google.auth import iam
from google.oauth2 import service_account as _sa
from google.cloud import storage
from google.api_core import retry as google_retry

from app_service.providers.storage.base import StorageProvider

_RETRYABLE = google_retry.Retry(deadline=600)


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
        blob.download_to_filename(local_path, retry=_RETRYABLE)
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

    def upload_text(self, text: str, destination_name: str) -> str:
        bucket = self.client.bucket(self.output_bucket)
        blob = bucket.blob(destination_name)
        blob.upload_from_string(text, content_type="application/json")
        return f"gs://{self.output_bucket}/{destination_name}"

    @contextlib.contextmanager
    def open_writer(self, destination_name: str):
        bucket = self.client.bucket(self.input_bucket)
        blob = bucket.blob(destination_name)
        uri = f"gs://{self.input_bucket}/{destination_name}"
        # blob.open("wb") hace un resumable upload por trozos sin cargar
        # el archivo entero en memoria del proceso.
        with blob.open("wb") as f:
            f.uri = uri  # exponer .uri como en el writer local
            yield f

    def generate_upload_signed_url(self, destination_name: str, expiration_seconds: int = 900) -> tuple[str, str]:
        # Cloud Run credentials (Compute Engine) have no private key, so we
        # delegate signing to the IAM signBlob API.
        creds, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        signer = iam.Signer(auth_req, creds, creds.service_account_email)
        signing_creds = _sa.Credentials(
            signer=signer,
            service_account_email=creds.service_account_email,
            token_uri="https://oauth2.googleapis.com/token",
        )
        bucket = self.client.bucket(self.input_bucket)
        blob = bucket.blob(destination_name)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expiration_seconds),
            method="PUT",
            content_type="application/octet-stream",
            credentials=signing_creds,
        )
        return url, f"gs://{self.input_bucket}/{destination_name}"


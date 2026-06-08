from app_service.config import Settings
from app_service.providers.database.session import build_session_factory
from app_service.providers.queue.base import QueueProvider
from app_service.providers.queue.sync import SyncQueueProvider
from app_service.providers.storage.base import StorageProvider
from app_service.providers.storage.local import LocalStorageProvider


def build_storage(settings: Settings) -> StorageProvider:
    if settings.storage_backend == "gcs":
        from app_service.providers.storage.gcs import GCSStorageProvider
        return GCSStorageProvider(settings.gcp_project_id, settings.gcs_input_bucket, settings.gcs_output_bucket)
    return LocalStorageProvider(settings.local_storage_path)


def build_queue(settings: Settings) -> QueueProvider:
    if settings.queue_backend == "pubsub":
        from app_service.providers.queue.pubsub import PubSubQueueProvider
        return PubSubQueueProvider(settings.gcp_project_id, settings.pubsub_topic, settings.pubsub_subscription)
    if settings.queue_backend == "redis":
        from app_service.providers.queue.redis_queue import RedisQueueProvider
        return RedisQueueProvider(settings.redis_url)
    return SyncQueueProvider()


def build_analysis_runner(settings: Settings):
    from app_service.providers.analysis.local import LocalPipelineRunner
    return LocalPipelineRunner(settings)


def build_session(settings: Settings):
    return build_session_factory(settings)


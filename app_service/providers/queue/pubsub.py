import json

from google.cloud import pubsub_v1

from app_service.providers.queue.base import QueueProvider, JobHandler


class PubSubQueueProvider(QueueProvider):
    def __init__(self, project_id: str, topic: str, subscription: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_path = self.publisher.topic_path(project_id, topic)
        self.subscription_path = self.subscriber.subscription_path(project_id, subscription)

    def enqueue(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.publisher.publish(self.topic_path, data).result(timeout=20)

    def consume_forever(self, handler: JobHandler) -> None:
        def callback(message: pubsub_v1.subscriber.message.Message):
            try:
                payload = json.loads(message.data.decode("utf-8"))
                handler(payload)
                message.ack()
            except Exception:
                message.nack()

        streaming = self.subscriber.subscribe(self.subscription_path, callback=callback)
        streaming.result()


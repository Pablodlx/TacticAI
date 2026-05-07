import json

import redis

from app_service.providers.queue.base import QueueProvider, JobHandler


class RedisQueueProvider(QueueProvider):
    def __init__(self, redis_url: str, queue_name: str = "tacticeye_jobs"):
        self.client = redis.Redis.from_url(redis_url)
        self.queue_name = queue_name

    def enqueue(self, payload: dict) -> None:
        self.client.rpush(self.queue_name, json.dumps(payload))

    def consume_forever(self, handler: JobHandler) -> None:
        while True:
            _, value = self.client.blpop(self.queue_name)
            payload = json.loads(value.decode("utf-8"))
            handler(payload)


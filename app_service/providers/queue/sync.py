import time
from collections import deque

from app_service.providers.queue.base import QueueProvider, JobHandler


class SyncQueueProvider(QueueProvider):
    def __init__(self):
        self._queue: deque[dict] = deque()

    def enqueue(self, payload: dict) -> None:
        self._queue.append(payload)

    def pop_nowait(self) -> dict | None:
        if self._queue:
            return self._queue.popleft()
        return None

    def consume_forever(self, handler: JobHandler) -> None:
        while True:
            item = self.pop_nowait()
            if item is None:
                time.sleep(1.0)
                continue
            handler(item)


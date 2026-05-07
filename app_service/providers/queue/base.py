from abc import ABC, abstractmethod
from typing import Callable


JobHandler = Callable[[dict], None]


class QueueProvider(ABC):
    @abstractmethod
    def enqueue(self, payload: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def consume_forever(self, handler: JobHandler) -> None:
        raise NotImplementedError


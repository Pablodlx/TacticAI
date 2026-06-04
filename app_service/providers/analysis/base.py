from abc import ABC, abstractmethod
from typing import Callable, Optional


class AnalysisRunner(ABC):
    @abstractmethod
    def run(
        self,
        job_id: str,
        local_input_path: str,
        output_dir: str,
        on_batch_complete: Optional[Callable] = None,
    ) -> dict:
        raise NotImplementedError


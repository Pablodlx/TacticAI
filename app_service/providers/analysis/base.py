from abc import ABC, abstractmethod


class AnalysisRunner(ABC):
    @abstractmethod
    def run(self, job_id: str, local_input_path: str, output_dir: str) -> dict:
        raise NotImplementedError


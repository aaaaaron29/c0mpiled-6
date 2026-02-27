"""BaseTool ABC and ToolResult dataclass."""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ToolResult:
    success: bool
    data: pd.DataFrame
    metadata: dict
    errors: list
    tool_name: str
    elapsed_seconds: float = 0.0


class BaseTool(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def run(self, data: pd.DataFrame, config=None, progress_callback=None) -> ToolResult:
        ...

    @abstractmethod
    def validate_input(self, data: pd.DataFrame) -> tuple[bool, list]:
        ...

    def _timed_run(self, data: pd.DataFrame, config=None, progress_callback=None) -> ToolResult:
        start = time.time()
        result = self.run(data, config=config, progress_callback=progress_callback)
        result.elapsed_seconds = time.time() - start
        return result

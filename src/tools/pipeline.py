"""Sequential tool chaining."""
import pandas as pd
from src.tools.base import BaseTool, ToolResult


class Pipeline:
    """Chains tools sequentially — each tool's output feeds into the next."""

    def __init__(self, tools: list[BaseTool]):
        self.tools = tools

    def run(self, data: pd.DataFrame, config=None, progress_callback=None) -> list[ToolResult]:
        results = []
        current_data = data.copy()

        for i, tool in enumerate(self.tools):
            valid, errors = tool.validate_input(current_data)
            if not valid:
                from src.tools.base import ToolResult
                import time
                results.append(ToolResult(
                    success=False,
                    data=current_data,
                    metadata={},
                    errors=errors,
                    tool_name=tool.name,
                ))
                break

            cb = None
            if progress_callback:
                def cb(p, msg, tool_idx=i, total=len(self.tools)):
                    progress_callback((tool_idx + p) / total, f"[{tool.name}] {msg}")

            result = tool.run(current_data, config=config, progress_callback=cb)
            results.append(result)

            if result.success:
                current_data = result.data

        return results

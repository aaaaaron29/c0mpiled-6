"""LabelingTool: wraps the LangGraph pipeline."""
import time
import pandas as pd
from src.tools.base import BaseTool, ToolResult
from src.models import LabelingTask
from src.ingestion import get_text_column


class LabelingTool(BaseTool):
    name = "LabelingTool"
    description = "Labels dataset rows using the LangGraph labeler-critic-validator pipeline."

    def __init__(self, task_type: str = "sentiment", modality: str = "TEXT"):
        self.task_type = task_type
        self.modality = modality

    def validate_input(self, data: pd.DataFrame) -> tuple[bool, list]:
        if data is None or len(data) == 0:
            return False, ["DataFrame is empty"]
        return True, []

    def run(self, data: pd.DataFrame, config=None, progress_callback=None) -> ToolResult:
        from src.graph import run_labeling_graph
        from src.config import get_config

        if config is None:
            config = get_config()

        start = time.time()
        df = data.copy()
        text_col = get_text_column(df)

        results = []
        total = len(df)
        errors = []

        for i, (idx, row) in enumerate(df.iterrows()):
            text = str(row.get(text_col, ""))
            task = LabelingTask(
                data_id=str(idx),
                modality=self.modality,
                task_type=self.task_type,
                text_content=text,
            )

            try:
                result = run_labeling_graph(task, config)
                results.append(result)
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                results.append({
                    "data_id": str(idx),
                    "label": "ERROR",
                    "confidence": 0,
                    "reasoning": str(e),
                    "final_confidence": 0,
                    "retry_count": 0,
                })

            if progress_callback:
                progress_callback((i + 1) / total, f"Labeled {i+1}/{total} items...")

        # Merge results back
        results_df = pd.DataFrame(results)
        results_df["data_id"] = results_df["data_id"].astype(str)
        df = df.reset_index(drop=True)
        df.index = df.index.astype(str)

        for col in ["label", "confidence", "reasoning", "final_confidence", "retry_count"]:
            if col in results_df.columns:
                df[col] = results_df[col].values

        df["fallback_to_human"] = results_df.get("fallback_reason", pd.Series([""] * len(df))).notna()

        metadata = {
            "total_rows": total,
            "labeled": len([r for r in results if r.get("label", "ERROR") != "ERROR"]),
            "fallback_count": len([r for r in results if r.get("fallback_reason")]),
            "avg_confidence": sum(r.get("final_confidence", 0) for r in results) / max(len(results), 1),
        }

        return ToolResult(
            success=True,
            data=df,
            metadata=metadata,
            errors=errors,
            tool_name=self.name,
            elapsed_seconds=time.time() - start,
        )

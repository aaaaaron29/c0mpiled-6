"""CleaningTool: PII detection, dedup, quality scoring, outlier detection."""
import re
import time
import pandas as pd
from src.tools.base import BaseTool, ToolResult


PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
    (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE"),
    (r"\b\d{16}\b", "CREDIT_CARD"),
    (r"\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", "DATE"),
]


class CleaningTool(BaseTool):
    name = "CleaningTool"
    description = "Cleans datasets: handles missing values, detects PII, deduplicates, scores quality."

    def __init__(self, remove_pii=True, dedup=True, quality_filter=True, outlier_filter=False):
        self.remove_pii = remove_pii
        self.dedup = dedup
        self.quality_filter = quality_filter
        self.outlier_filter = outlier_filter

    def validate_input(self, data: pd.DataFrame) -> tuple[bool, list]:
        errors = []
        if data is None or len(data) == 0:
            errors.append("DataFrame is empty")
        if len(errors) > 0:
            return False, errors
        return True, []

    def run(self, data: pd.DataFrame, config=None, progress_callback=None) -> ToolResult:
        start = time.time()
        df = data.copy()
        metadata = {
            "original_rows": len(df),
            "pii_found": 0,
            "duplicates_removed": 0,
            "low_quality_removed": 0,
            "outliers_removed": 0,
        }
        errors = []

        # Step 1: Handle missing values
        df = df.dropna(how="all")
        df = df.fillna("")

        if progress_callback:
            progress_callback(0.2, "Handling missing values...")

        # Step 2: PII detection & masking
        if self.remove_pii:
            for col in df.select_dtypes(include="object").columns:
                pii_count = 0
                def mask_pii(text):
                    nonlocal pii_count
                    if not isinstance(text, str):
                        return text
                    for pattern, label in PII_PATTERNS:
                        matches = re.findall(pattern, text)
                        if matches:
                            pii_count += len(matches)
                            text = re.sub(pattern, f"[{label}_REDACTED]", text)
                    return text
                df[col] = df[col].apply(mask_pii)
                metadata["pii_found"] += pii_count

        if progress_callback:
            progress_callback(0.4, "PII detection complete...")

        # Step 3: Deduplication
        if self.dedup:
            before = len(df)
            df = df.drop_duplicates()
            metadata["duplicates_removed"] = before - len(df)

        if progress_callback:
            progress_callback(0.6, "Deduplication complete...")

        # Step 4: Quality scoring
        text_cols = df.select_dtypes(include="object").columns.tolist()
        if text_cols:
            primary_col = text_cols[0]
            df["_quality_score"] = df[primary_col].apply(_quality_score)
            if self.quality_filter:
                before = len(df)
                df = df[df["_quality_score"] >= 0.3]
                metadata["low_quality_removed"] = before - len(df)

        if progress_callback:
            progress_callback(0.8, "Quality scoring complete...")

        # Step 5: Outlier detection (numeric columns)
        if self.outlier_filter:
            num_cols = df.select_dtypes(include="number").columns.tolist()
            # Remove _quality_score from outlier detection
            num_cols = [c for c in num_cols if c != "_quality_score"]
            if num_cols:
                before = len(df)
                for col in num_cols:
                    q1 = df[col].quantile(0.25)
                    q3 = df[col].quantile(0.75)
                    iqr = q3 - q1
                    df = df[(df[col] >= q1 - 3 * iqr) & (df[col] <= q3 + 3 * iqr)]
                metadata["outliers_removed"] = before - len(df)

        if progress_callback:
            progress_callback(1.0, "Done!")

        metadata["final_rows"] = len(df)

        return ToolResult(
            success=True,
            data=df,
            metadata=metadata,
            errors=errors,
            tool_name=self.name,
            elapsed_seconds=time.time() - start,
        )


def _quality_score(text: str) -> float:
    if not isinstance(text, str) or len(text.strip()) == 0:
        return 0.0
    score = 1.0
    if len(text.strip()) < 5:
        score -= 0.5
    words = text.split()
    if len(words) == 0:
        return 0.0
    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.3:
        score -= 0.3
    if len(text) > 10000:
        score -= 0.1
    return max(0.0, min(1.0, score))

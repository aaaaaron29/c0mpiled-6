"""Data export utilities."""
import io
import json
import pandas as pd


def export_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def export_json(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", indent=2).encode("utf-8")


def export_jsonl(df: pd.DataFrame) -> bytes:
    lines = [json.dumps(row) for row in df.to_dict(orient="records")]
    return "\n".join(lines).encode("utf-8")


def get_export_bytes(df: pd.DataFrame, fmt: str) -> tuple[bytes, str, str]:
    """Returns (bytes, filename, mime_type) for the given format."""
    if fmt == "csv":
        return export_csv(df), "export.csv", "text/csv"
    elif fmt == "jsonl":
        return export_jsonl(df), "export.jsonl", "application/jsonl"
    else:
        return export_json(df), "export.json", "application/json"

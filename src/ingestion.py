"""CSV/JSON/JSONL data loading."""
import io
import pandas as pd


def load_data(uploaded_file) -> pd.DataFrame:
    """Load data from uploaded file (CSV, JSON, JSONL) into a DataFrame."""
    name = uploaded_file.name.lower()
    content = uploaded_file.read()

    try:
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content), encoding="utf-8", on_bad_lines="skip")
        elif name.endswith(".jsonl"):
            lines = content.decode("utf-8", errors="replace").strip().split("\n")
            import json
            records = []
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
            return pd.DataFrame(records)
        elif name.endswith(".json"):
            import json
            data = json.loads(content.decode("utf-8", errors="replace"))
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try common keys
                for key in ["data", "records", "items", "rows"]:
                    if key in data and isinstance(data[key], list):
                        return pd.DataFrame(data[key])
                return pd.DataFrame([data])
            return pd.DataFrame([data])
        else:
            # Try CSV as fallback
            return pd.read_csv(io.BytesIO(content), encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        raise ValueError(f"Failed to load file '{uploaded_file.name}': {str(e)}")


def get_text_column(df: pd.DataFrame) -> str:
    """Guess the primary text column name."""
    candidates = ["text", "content", "description", "input", "data", "sentence", "review", "comment"]
    for col in candidates:
        if col in df.columns:
            return col
    # Fall back to first string column
    for col in df.columns:
        if df[col].dtype == object:
            return col
    return df.columns[0] if len(df.columns) > 0 else "text"

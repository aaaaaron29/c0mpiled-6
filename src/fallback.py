"""Human review queue (JSON file based)."""
import json
import os
import datetime
from src.models import HumanReviewItem
from src.config import SystemConfig, get_config


def _ensure_dir(config: SystemConfig):
    os.makedirs(config.review_queue_dir, exist_ok=True)


def write_to_review_queue(item: HumanReviewItem, config: SystemConfig = None):
    if config is None:
        config = get_config()
    _ensure_dir(config)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(config.review_queue_dir, f"{item.data_id}_{ts}.json")
    with open(path, "w") as f:
        json.dump(item.model_dump(), f, indent=2)


def load_review_queue(config: SystemConfig = None) -> list[HumanReviewItem]:
    if config is None:
        config = get_config()
    _ensure_dir(config)
    items = []
    for fname in sorted(os.listdir(config.review_queue_dir)):
        if fname.endswith(".json"):
            path = os.path.join(config.review_queue_dir, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                items.append(HumanReviewItem(**data))
            except Exception:
                pass
    return items


def get_review_queue_summary(config: SystemConfig = None) -> dict:
    items = load_review_queue(config)
    reasons = {}
    for item in items:
        reasons[item.fallback_reason] = reasons.get(item.fallback_reason, 0) + 1
    return {"total": len(items), "by_reason": reasons}


def export_review_queue_to_csv(config: SystemConfig = None) -> bytes:
    import pandas as pd
    items = load_review_queue(config)
    if not items:
        return b""
    rows = []
    for item in items:
        rows.append({
            "data_id": item.data_id,
            "fallback_reason": item.fallback_reason,
            "timestamp": item.timestamp,
            "error_log": " | ".join(item.error_log),
            "original_input": json.dumps(item.original_input),
        })
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def clear_review_queue(config: SystemConfig = None, confirm: bool = False):
    if not confirm:
        return
    if config is None:
        config = get_config()
    _ensure_dir(config)
    for fname in os.listdir(config.review_queue_dir):
        if fname.endswith(".json"):
            os.remove(os.path.join(config.review_queue_dir, fname))


def delete_review_item(data_id: str, config: SystemConfig = None):
    if config is None:
        config = get_config()
    _ensure_dir(config)
    for fname in os.listdir(config.review_queue_dir):
        if fname.startswith(data_id) and fname.endswith(".json"):
            os.remove(os.path.join(config.review_queue_dir, fname))

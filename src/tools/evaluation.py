"""EvaluationTool: classification metrics from scratch."""
import time
import pandas as pd
from collections import defaultdict
from src.tools.base import BaseTool, ToolResult


class EvaluationTool(BaseTool):
    name = "EvaluationTool"
    description = "Computes classification metrics: precision, recall, F1, accuracy, ECE."

    def __init__(self, pred_col: str = "label", gt_col: str = "ground_truth"):
        self.pred_col = pred_col
        self.gt_col = gt_col

    def validate_input(self, data: pd.DataFrame) -> tuple[bool, list]:
        errors = []
        if self.pred_col not in data.columns:
            errors.append(f"Missing prediction column: {self.pred_col}")
        if self.gt_col not in data.columns:
            errors.append(f"Missing ground truth column: {self.gt_col}")
        return len(errors) == 0, errors

    def run(self, data: pd.DataFrame, config=None, progress_callback=None) -> ToolResult:
        start = time.time()
        valid, errors = self.validate_input(data)
        if not valid:
            return ToolResult(success=False, data=data, metadata={}, errors=errors,
                              tool_name=self.name, elapsed_seconds=0)

        preds = data[self.pred_col].astype(str).tolist()
        gts = data[self.gt_col].astype(str).tolist()
        classes = sorted(set(preds + gts))

        # Per-class metrics
        tp = defaultdict(int)
        fp = defaultdict(int)
        fn = defaultdict(int)

        for p, g in zip(preds, gts):
            if p == g:
                tp[g] += 1
            else:
                fp[p] += 1
                fn[g] += 1

        per_class = {}
        for cls in classes:
            prec = tp[cls] / max(tp[cls] + fp[cls], 1)
            rec = tp[cls] / max(tp[cls] + fn[cls], 1)
            f1 = 2 * prec * rec / max(prec + rec, 1e-9)
            per_class[cls] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}

        # Aggregate
        total = len(preds)
        accuracy = sum(1 for p, g in zip(preds, gts) if p == g) / max(total, 1)
        macro_f1 = sum(v["f1"] for v in per_class.values()) / max(len(per_class), 1)

        # ECE (if confidence column exists)
        ece = None
        if "confidence" in data.columns or "final_confidence" in data.columns:
            conf_col = "final_confidence" if "final_confidence" in data.columns else "confidence"
            confs = data[conf_col].fillna(50).astype(float) / 100.0
            correct = [1 if p == g else 0 for p, g in zip(preds, gts)]
            ece = _compute_ece(confs.tolist(), correct)

        metadata = {
            "accuracy": round(accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "per_class": per_class,
            "total_samples": total,
            "ece": round(ece, 4) if ece is not None else None,
        }

        return ToolResult(
            success=True,
            data=data,
            metadata=metadata,
            errors=[],
            tool_name=self.name,
            elapsed_seconds=time.time() - start,
        )


def _compute_ece(confidences: list, correct: list, n_bins: int = 10) -> float:
    bins = [[] for _ in range(n_bins)]
    for conf, corr in zip(confidences, correct):
        idx = min(int(conf * n_bins), n_bins - 1)
        bins[idx].append((conf, corr))

    ece = 0.0
    n = len(confidences)
    for bin_items in bins:
        if not bin_items:
            continue
        avg_conf = sum(c for c, _ in bin_items) / len(bin_items)
        avg_acc = sum(corr for _, corr in bin_items) / len(bin_items)
        ece += abs(avg_conf - avg_acc) * len(bin_items) / max(n, 1)
    return ece

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, computed_field


class BoundingBox(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    label: str


class LabelPrediction(BaseModel):
    label: str
    confidence: int  # 0-100
    reasoning: str
    bounding_boxes: list[BoundingBox] = []


class CriticReview(BaseModel):
    is_correct: bool
    confidence_score: int
    critique: str


class LabelingTask(BaseModel):
    data_id: str
    modality: str  # TEXT | IMAGE | HYBRID
    task_type: str
    text_content: str = ""
    image_path: str = ""


class ValidatedLabel(BaseModel):
    data_id: str
    label: str
    confidence: int
    reasoning: str
    critic_confidence: int
    retry_count: int

    @computed_field
    @property
    def final_confidence(self) -> int:
        return (self.confidence + self.critic_confidence) // 2


class FallbackReason(str, Enum):
    RETRY_LIMIT = "RETRY_LIMIT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARSING_ERROR = "PARSING_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class HumanReviewItem(BaseModel):
    data_id: str
    original_input: dict
    labeler_attempts: list[dict]
    critic_reviews: list[dict]
    error_log: list[str]
    fallback_reason: str
    timestamp: str

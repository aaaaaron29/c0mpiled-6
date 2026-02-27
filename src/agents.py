"""LangGraph agent node implementations."""
import json
import os
from typing import Optional
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.config import get_config, get_llm
from src.models import LabelPrediction, CriticReview, FallbackReason
from src.prompts import get_labeling_prompt, get_critic_prompt


def _safe_parse_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response text."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try markdown code block
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    # Try finding first {...}
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def _load_rubric(task_type: str) -> dict:
    rubric_path = os.path.join("config", "rubrics", f"{task_type.lower()}.json")
    if os.path.exists(rubric_path):
        with open(rubric_path) as f:
            return json.load(f)
    return {}


def labeler_node(state: dict) -> Command:
    """Labels the input data, incorporating critic feedback on retry."""
    config = get_config()
    llm = get_llm(config.labeler_model)

    critic_feedback = ""
    if state.get("critic_review") and not state["critic_review"].get("is_correct", True):
        critic_feedback = state["critic_review"].get("critique", "")

    text_content = state["input_data"].get("text_content", str(state["input_data"]))
    prompt = get_labeling_prompt(state["task_type"], text_content, critic_feedback)

    error_log = list(state.get("error_log", []))
    labeler_output = None

    for attempt in range(2):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            parsed = _safe_parse_json(response.content)
            if parsed:
                # Validate with Pydantic
                pred = LabelPrediction(**parsed)
                labeler_output = pred.model_dump()
                break
        except Exception as e:
            error_log.append(f"Labeler attempt {attempt + 1} failed: {str(e)}")

    if labeler_output is None:
        error_log.append("Labeler: all attempts failed, sending to fallback")
        return Command(
            goto="fallback_node",
            update={
                "fallback_to_human": True,
                "error_log": error_log,
                "labeler_output": {"label": "UNKNOWN", "confidence": 0, "reasoning": "Parse error", "bounding_boxes": []},
            }
        )

    attempts = list(state.get("labeler_attempts", []))
    attempts.append(labeler_output)

    return Command(
        goto="critic_node",
        update={
            "labeler_output": labeler_output,
            "labeler_attempts": attempts,
            "error_log": error_log,
        }
    )


def critic_node(state: dict) -> Command:
    """Evaluates the labeler's output and routes accordingly."""
    config = get_config()
    llm = get_llm(config.critic_model)

    rubric = _load_rubric(state["task_type"])
    text_content = state["input_data"].get("text_content", str(state["input_data"]))
    prompt = get_critic_prompt(
        state["task_type"],
        text_content,
        state["labeler_output"],
        rubric,
    )

    error_log = list(state.get("error_log", []))
    critic_review = None

    for attempt in range(2):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            parsed = _safe_parse_json(response.content)
            if parsed:
                review = CriticReview(**parsed)
                critic_review = review.model_dump()
                break
        except Exception as e:
            error_log.append(f"Critic attempt {attempt + 1} failed: {str(e)}")

    if critic_review is None:
        # Default: accept the label
        critic_review = {"is_correct": True, "confidence_score": 70, "critique": "Critic parse error - accepting label"}

    reviews = list(state.get("critic_reviews", []))
    reviews.append(critic_review)
    retry_count = state.get("retry_count", 0)

    if critic_review["is_correct"]:
        return Command(
            goto="validator_node",
            update={"critic_review": critic_review, "critic_reviews": reviews, "error_log": error_log}
        )
    elif retry_count < state.get("max_retries", 3):
        return Command(
            goto="labeler_node",
            update={
                "critic_review": critic_review,
                "critic_reviews": reviews,
                "retry_count": retry_count + 1,
                "error_log": error_log,
            }
        )
    else:
        error_log.append("Critic: max retries reached, sending to fallback")
        return Command(
            goto="fallback_node",
            update={
                "critic_review": critic_review,
                "critic_reviews": reviews,
                "fallback_to_human": True,
                "error_log": error_log,
            }
        )


def validator_node(state: dict) -> Command:
    """Validates confidence threshold and constructs final output."""
    config = get_config()
    labeler_output = state["labeler_output"]
    critic_review = state["critic_review"]

    labeler_conf = labeler_output.get("confidence", 0)
    critic_conf = critic_review.get("confidence_score", 0)
    final_conf = (labeler_conf + critic_conf) // 2

    if final_conf < config.min_confidence_threshold:
        return Command(
            goto="fallback_node",
            update={
                "fallback_to_human": True,
                "error_log": list(state.get("error_log", [])) + [
                    f"Validator: confidence {final_conf} below threshold {config.min_confidence_threshold}"
                ],
            }
        )

    validated = {
        "data_id": state["data_id"],
        "label": labeler_output["label"],
        "confidence": labeler_conf,
        "reasoning": labeler_output.get("reasoning", ""),
        "critic_confidence": critic_conf,
        "final_confidence": final_conf,
        "retry_count": state.get("retry_count", 0),
    }

    return Command(
        goto="__end__",
        update={"validated_output": validated, "fallback_to_human": False}
    )


def fallback_node(state: dict) -> Command:
    """Writes item to human review queue."""
    from src.fallback import write_to_review_queue
    from src.models import HumanReviewItem
    import datetime

    labeler_output = state.get("labeler_output", {})
    critic_review = state.get("critic_review", {})
    retry_count = state.get("retry_count", 0)

    # Determine fallback reason
    error_log = state.get("error_log", [])
    if retry_count >= state.get("max_retries", 3):
        reason = FallbackReason.RETRY_LIMIT
    elif "confidence" in str(error_log):
        reason = FallbackReason.LOW_CONFIDENCE
    elif "Parse error" in str(error_log):
        reason = FallbackReason.PARSING_ERROR
    else:
        reason = FallbackReason.VALIDATION_ERROR

    item = HumanReviewItem(
        data_id=state["data_id"],
        original_input=state["input_data"],
        labeler_attempts=state.get("labeler_attempts", []),
        critic_reviews=state.get("critic_reviews", []),
        error_log=error_log,
        fallback_reason=reason.value,
        timestamp=datetime.datetime.utcnow().isoformat(),
    )

    try:
        config = get_config()
        write_to_review_queue(item, config)
    except Exception as e:
        pass  # Don't crash the pipeline on queue write failure

    return Command(
        goto="__end__",
        update={
            "validated_output": {
                "data_id": state["data_id"],
                "label": labeler_output.get("label", "UNKNOWN"),
                "confidence": labeler_output.get("confidence", 0),
                "reasoning": "Sent to human review",
                "critic_confidence": critic_review.get("confidence_score", 0),
                "final_confidence": 0,
                "retry_count": retry_count,
                "fallback_reason": reason.value,
            }
        }
    )

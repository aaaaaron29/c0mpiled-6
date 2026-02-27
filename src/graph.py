"""LangGraph state machine for the labeling pipeline."""
from typing import Optional, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from src.agents import labeler_node, critic_node, validator_node, fallback_node
from src.models import LabelingTask
from src.config import SystemConfig, get_config


class LabelingState(TypedDict):
    data_id: str
    input_data: dict
    modality: str
    task_type: str
    labeler_output: Optional[dict]
    critic_review: Optional[dict]
    retry_count: int
    max_retries: int
    validated_output: Optional[dict]
    fallback_to_human: bool
    error_log: list
    image_data: Optional[dict]
    labeler_attempts: list
    critic_reviews: list


def build_graph():
    graph = StateGraph(LabelingState)
    graph.add_node("labeler_node", labeler_node)
    graph.add_node("critic_node", critic_node)
    graph.add_node("validator_node", validator_node)
    graph.add_node("fallback_node", fallback_node)
    graph.set_entry_point("labeler_node")
    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_labeling_graph(task: LabelingTask, config: SystemConfig = None) -> dict:
    """Run the labeling pipeline for a single task. Returns validated output dict."""
    if config is None:
        config = get_config()

    graph = get_graph()

    initial_state: LabelingState = {
        "data_id": task.data_id,
        "input_data": {
            "text_content": task.text_content,
            "image_path": task.image_path,
            "modality": task.modality,
        },
        "modality": task.modality,
        "task_type": task.task_type,
        "labeler_output": None,
        "critic_review": None,
        "retry_count": 0,
        "max_retries": config.max_retries,
        "validated_output": None,
        "fallback_to_human": False,
        "error_log": [],
        "image_data": None,
        "labeler_attempts": [],
        "critic_reviews": [],
    }

    try:
        final_state = graph.invoke(initial_state)
        return final_state.get("validated_output", {
            "data_id": task.data_id,
            "label": "ERROR",
            "confidence": 0,
            "reasoning": "Graph execution failed",
            "critic_confidence": 0,
            "final_confidence": 0,
            "retry_count": 0,
        })
    except Exception as e:
        return {
            "data_id": task.data_id,
            "label": "ERROR",
            "confidence": 0,
            "reasoning": f"Graph error: {str(e)}",
            "critic_confidence": 0,
            "final_confidence": 0,
            "retry_count": 0,
        }

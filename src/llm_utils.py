"""Shared LLM call wrapper and robust JSON parsing."""
import re
import json
from src.config import get_config, get_llm


def call_llm(prompt: str, config=None) -> str:
    """Simple wrapper around the project's LLM. Returns raw text response."""
    if config is None:
        config = get_config()
    try:
        llm = get_llm(config.labeler_model)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"[LLM ERROR: {str(e)}]"


def parse_llm_json(response_text: str) -> dict | None:
    """
    Robustly extract JSON from LLM response.
    Handles: raw JSON, markdown code blocks, partial/noisy output.
    """
    if not response_text or response_text.startswith("[LLM ERROR"):
        return None

    text = response_text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Markdown code block: ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # 3. First complete JSON object {...}
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 4. First complete JSON array [...]
    match = re.search(r"\[[\s\S]+\]", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 5. Try fixing common LLM JSON mistakes (trailing commas, single quotes)
    try:
        cleaned = re.sub(r",\s*([}\]])", r"\1", text)  # trailing commas
        cleaned = cleaned.replace("'", '"')  # single quotes
        match = re.search(r"\{[\s\S]+\}", cleaned)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return None

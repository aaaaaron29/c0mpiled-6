import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SystemConfig:
    # API
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    # Models
    labeler_model: str = field(default_factory=lambda: os.getenv("LABELER_MODEL", "gpt-5-mini"))
    critic_model: str = field(default_factory=lambda: os.getenv("CRITIC_MODEL", "gpt-5-mini"))
    vision_model: str = field(default_factory=lambda: os.getenv("VISION_MODEL", "gpt-5-mini"))
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.1")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096")))
    # Fallback
    max_retries: int = 3
    min_confidence_threshold: int = 85
    # Paths
    data_dir: str = "data"
    output_dir: str = "data/output"
    review_queue_dir: str = "data/review_queue"


_config_instance = None


def get_config() -> SystemConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = SystemConfig()
    return _config_instance


def get_llm(model_name: str = None):
    from langchain_openai import ChatOpenAI
    config = get_config()
    model = model_name or config.labeler_model
    return ChatOpenAI(
        model=model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        api_key=config.openai_api_key,
    )

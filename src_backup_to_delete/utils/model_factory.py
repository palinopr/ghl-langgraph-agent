"""
Model factory for creating properly configured LLM instances
Ensures tool calling is properly supported
"""
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.config import get_settings
from app.utils.simple_logger import get_logger

logger = get_logger("model_factory")


def create_openai_model(model_name: str = None, temperature: float = 0.0):
    """
    Create a properly configured ChatOpenAI instance
    This ensures tool calling works correctly
    """
    settings = get_settings()
    model = model_name or settings.openai_model
    
    # Create explicit ChatOpenAI instance
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_retries=3,
        timeout=30,
        # Ensure we're using the latest API version that supports tools
        model_kwargs={
            "tools": None,  # Will be bound by create_react_agent
            "tool_choice": "auto"
        }
    )
    
    logger.info(f"Created ChatOpenAI model: {model} (temp={temperature})")
    return llm


def create_model_for_agent(provider: str = "openai", **kwargs):
    """
    Factory method to create models for agents
    Ensures proper configuration for tool calling
    """
    if provider == "openai":
        return create_openai_model(**kwargs)
    elif provider == "anthropic":
        # Alternative that's known to work well with tools
        settings = get_settings()
        return ChatAnthropic(
            model="claude-3-opus-20240229",
            temperature=kwargs.get("temperature", 0.0),
            max_retries=3
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
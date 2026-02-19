"""Factory for creating LLM instances based on provider configuration."""

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import get_config, LLMProvider


def create_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> BaseChatModel:
    """Create an LLM instance based on the specified provider.

    Args:
        provider: LLM provider (anthropic, openai, ollama). Defaults to config.
        model: Model name. Defaults to config.
        max_tokens: Maximum tokens for response. Defaults to config.
        **kwargs: Additional arguments passed to the LLM constructor.

    Returns:
        Configured LLM instance.

    Raises:
        ValueError: If provider is not supported or API key is missing.
    """
    config = get_config()

    provider = provider or config.llm_provider
    model = model or config.model_name
    max_tokens = max_tokens or config.max_tokens

    if provider == LLMProvider.ANTHROPIC:
        return _create_anthropic_llm(model, max_tokens, config.anthropic_api_key, **kwargs)
    elif provider == LLMProvider.OPENAI:
        return _create_openai_llm(model, max_tokens, config.openai_api_key, **kwargs)
    elif provider == LLMProvider.OLLAMA:
        return _create_ollama_llm(model, max_tokens, config.ollama_base_url, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_anthropic_llm(
    model: str,
    max_tokens: int,
    api_key: str,
    **kwargs,
) -> BaseChatModel:
    """Create an Anthropic Claude LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required for Anthropic provider. "
            "Install it with: pip install langchain-anthropic"
        )

    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required. "
            "Set it in your .env file or environment variables."
        )

    return ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
        **kwargs,
    )


def _create_openai_llm(
    model: str,
    max_tokens: int,
    api_key: str,
    **kwargs,
) -> BaseChatModel:
    """Create an OpenAI GPT LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required for OpenAI provider. "
            "Install it with: pip install langchain-openai"
        )

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is required. "
            "Set it in your .env file or environment variables."
        )

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
        **kwargs,
    )


def _create_ollama_llm(
    model: str,
    max_tokens: int,
    base_url: str,
    **kwargs,
) -> BaseChatModel:
    """Create an Ollama LLM instance for local models."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError(
            "langchain-ollama is required for Ollama provider. "
            "Install it with: pip install langchain-ollama"
        )

    return ChatOllama(
        model=model,
        base_url=base_url,
        num_predict=max_tokens,
        **kwargs,
    )


# Alias for backwards compatibility
create_chat_model = create_llm

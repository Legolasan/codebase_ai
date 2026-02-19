"""Factory for creating embedding instances based on provider configuration."""

from typing import Optional

from langchain_core.embeddings import Embeddings

from ..config import get_config, EmbeddingProvider


def create_embeddings(
    provider: Optional[EmbeddingProvider] = None,
    model: Optional[str] = None,
    **kwargs,
) -> Embeddings:
    """Create an embeddings instance based on the specified provider.

    Args:
        provider: Embedding provider (huggingface, openai, ollama). Defaults to config.
        model: Model name. Defaults to config.
        **kwargs: Additional arguments passed to the embeddings constructor.

    Returns:
        Configured embeddings instance.

    Raises:
        ValueError: If provider is not supported.
    """
    config = get_config()

    provider = provider or config.embedding_provider
    model = model or config.embedding_model

    if provider == EmbeddingProvider.HUGGINGFACE:
        return _create_huggingface_embeddings(model, **kwargs)
    elif provider == EmbeddingProvider.OPENAI:
        return _create_openai_embeddings(model, config.openai_api_key, **kwargs)
    elif provider == EmbeddingProvider.OLLAMA:
        return _create_ollama_embeddings(model, config.ollama_base_url, **kwargs)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def _create_huggingface_embeddings(model: str, **kwargs) -> Embeddings:
    """Create HuggingFace embeddings (runs locally, free)."""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        raise ImportError(
            "langchain-community is required for HuggingFace embeddings. "
            "Install it with: pip install langchain-community sentence-transformers"
        )

    return HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
        **kwargs,
    )


def _create_openai_embeddings(model: str, api_key: str, **kwargs) -> Embeddings:
    """Create OpenAI embeddings."""
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        raise ImportError(
            "langchain-openai is required for OpenAI embeddings. "
            "Install it with: pip install langchain-openai"
        )

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is required for OpenAI embeddings. "
            "Set it in your .env file or environment variables."
        )

    return OpenAIEmbeddings(
        model=model,
        api_key=api_key,
        **kwargs,
    )


def _create_ollama_embeddings(model: str, base_url: str, **kwargs) -> Embeddings:
    """Create Ollama embeddings (runs locally)."""
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError:
        raise ImportError(
            "langchain-ollama is required for Ollama embeddings. "
            "Install it with: pip install langchain-ollama"
        )

    return OllamaEmbeddings(
        model=model,
        base_url=base_url,
        **kwargs,
    )

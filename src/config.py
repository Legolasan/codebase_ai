"""Configuration management for the coding assistant."""

import os
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# Default assistant config directory
ASSISTANT_CONFIG_DIR = Path.home() / ".assistant"


class PermissionMode(Enum):
    """Permission modes for agent file operations."""

    FULL_ACCESS = "full"    # Agents can read, write, execute
    READ_ONLY = "readonly"  # Agents can only read and suggest
    ASK_BEFORE = "ask"      # Prompt user before modifications


class LLMProvider(Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class EmbeddingProvider(Enum):
    """Supported embedding providers."""

    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    OLLAMA = "ollama"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.OLLAMA: "llama3",
}

DEFAULT_EMBEDDING_MODELS = {
    EmbeddingProvider.HUGGINGFACE: "sentence-transformers/all-MiniLM-L6-v2",
    EmbeddingProvider.OPENAI: "text-embedding-3-small",
    EmbeddingProvider.OLLAMA: "nomic-embed-text",
}


@dataclass
class Config:
    """Application configuration."""

    # LLM Provider settings
    llm_provider: LLMProvider = field(
        default_factory=lambda: LLMProvider(os.getenv("LLM_PROVIDER", "anthropic"))
    )

    model_name: str = field(
        default_factory=lambda: os.getenv("MODEL_NAME", "")
    )

    # API Keys (based on provider)
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Embedding settings
    embedding_provider: EmbeddingProvider = field(
        default_factory=lambda: EmbeddingProvider(os.getenv("EMBEDDING_PROVIDER", "huggingface"))
    )

    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "")
    )

    # ChromaDB settings
    chroma_persist_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIR", "./.chroma_db"))
    )

    # Permission mode
    permission_mode: PermissionMode = field(
        default_factory=lambda: PermissionMode(os.getenv("PERMISSION_MODE", "ask"))
    )

    # Performance tuning
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1500"))
    )

    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )

    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS", "4096"))
    )

    max_results: int = field(
        default_factory=lambda: int(os.getenv("MAX_RESULTS", "5"))
    )

    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "5"))
    )

    # Supported file extensions for indexing
    supported_extensions: tuple = (
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".go", ".rs", ".cpp", ".c", ".h",
        ".rb", ".php", ".swift", ".kt", ".scala",
        ".md", ".txt", ".json", ".yaml", ".yml",
        ".toml", ".ini", ".cfg", ".sh", ".bash",
    )

    # Directories to ignore during indexing
    ignore_dirs: tuple = (
        ".git", ".venv", "venv", "node_modules",
        "__pycache__", ".pytest_cache", ".mypy_cache",
        "dist", "build", ".eggs", "*.egg-info",
        ".chroma_db", ".idea", ".vscode",
    )

    def __post_init__(self):
        """Set default model names based on provider if not specified."""
        if not self.model_name:
            self.model_name = DEFAULT_MODELS.get(self.llm_provider, "claude-sonnet-4-20250514")

        if not self.embedding_model:
            self.embedding_model = DEFAULT_EMBEDDING_MODELS.get(
                self.embedding_provider,
                "sentence-transformers/all-MiniLM-L6-v2"
            )

    def get_api_key(self) -> str:
        """Get the API key for the current LLM provider."""
        if self.llm_provider == LLMProvider.ANTHROPIC:
            return self.anthropic_api_key
        elif self.llm_provider == LLMProvider.OPENAI:
            return self.openai_api_key
        elif self.llm_provider == LLMProvider.OLLAMA:
            return self.ollama_base_url  # Ollama uses base URL instead of API key
        return ""

    def validate(self) -> bool:
        """Validate configuration based on selected provider."""
        if self.llm_provider == LLMProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider.")
        elif self.llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI provider.")
        elif self.llm_provider == LLMProvider.OLLAMA:
            if not self.ollama_base_url:
                raise ValueError("OLLAMA_BASE_URL is required when using Ollama provider.")

        # Validate embedding provider if using OpenAI embeddings
        if self.embedding_provider == EmbeddingProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI embeddings.")

        return True


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the config instance (useful for testing)."""
    global _config
    _config = None


def set_permission_mode(mode: str) -> None:
    """Update permission mode at runtime."""
    config = get_config()
    config.permission_mode = PermissionMode(mode)


def get_config_dir() -> Path:
    """Get the assistant config directory, creating if needed."""
    ASSISTANT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return ASSISTANT_CONFIG_DIR


def get_plugin_config_path() -> Path:
    """Get the path to the plugin configuration file."""
    return get_config_dir() / "plugins.json"

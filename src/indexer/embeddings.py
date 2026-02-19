"""Embedding generation for code chunks."""

from typing import Optional

from langchain_core.embeddings import Embeddings

from ..config import get_config
from ..providers import create_embeddings, create_llm
from .file_loader import CodeChunk


class EmbeddingGenerator:
    """Generates embeddings for code chunks.

    Supports multiple embedding providers (HuggingFace, OpenAI, Ollama)
    via configuration.
    """

    def __init__(self):
        """Initialize embedding generator using configured provider."""
        self._embeddings: Optional[Embeddings] = None

    @property
    def embeddings(self) -> Embeddings:
        """Lazy load embeddings model from factory."""
        if self._embeddings is None:
            self._embeddings = create_embeddings()
        return self._embeddings

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return self.embeddings.embed_documents(texts)

    def embed_chunk(self, chunk: CodeChunk) -> list[float]:
        """Generate embedding for a code chunk.

        Prepends metadata context to improve retrieval quality.
        """
        # Add context to help with retrieval
        context = f"File: {chunk.file_path} | Language: {chunk.language}\n\n"
        text = context + chunk.content
        return self.embed_text(text)

    def embed_chunks(self, chunks: list[CodeChunk]) -> list[list[float]]:
        """Generate embeddings for multiple code chunks."""
        texts = []
        for chunk in chunks:
            context = f"File: {chunk.file_path} | Language: {chunk.language}\n\n"
            texts.append(context + chunk.content)
        return self.embed_texts(texts)

    @property
    def dimension(self) -> int:
        """Get embedding dimension size."""
        # Generate a test embedding to get dimension
        test_embedding = self.embed_text("test")
        return len(test_embedding)


class SemanticEmbeddingGenerator:
    """Alternative embedding generator using LLM for semantic understanding.

    Uses the configured LLM to generate descriptive summaries, then embeds those.
    More expensive but potentially better for code understanding.
    """

    def __init__(self):
        """Initialize with configured LLM and base embedder."""
        self.llm = create_llm()
        self.base_embedder = EmbeddingGenerator()

    def summarize_code(self, chunk: CodeChunk) -> str:
        """Generate a semantic summary of the code chunk."""
        prompt = f"""Briefly describe what this {chunk.language} code does in 1-2 sentences:

```{chunk.language}
{chunk.content}
```

Description:"""

        response = self.llm.invoke(prompt)
        return response.content

    def embed_chunk(self, chunk: CodeChunk) -> list[float]:
        """Generate embedding via summarization."""
        summary = self.summarize_code(chunk)
        # Combine original content with summary for rich embedding
        combined = f"{chunk.file_path}\n{summary}\n{chunk.content}"
        return self.base_embedder.embed_text(combined)

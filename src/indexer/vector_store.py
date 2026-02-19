"""Vector store operations using ChromaDB."""

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from ..config import get_config
from .file_loader import CodeChunk, FileLoader
from .embeddings import EmbeddingGenerator


class VectorStore:
    """ChromaDB-based vector store for code chunks."""

    def __init__(
        self,
        collection_name: str = "codebase",
        persist_dir: Optional[Path] = None,
    ):
        config = get_config()
        self.persist_dir = persist_dir or config.chroma_persist_dir
        self.collection_name = collection_name

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        # Initialize embedding generator
        self.embedder = EmbeddingGenerator()

        # Get or create collection
        self._collection = None

    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunk(self, chunk: CodeChunk) -> None:
        """Add a single code chunk to the store."""
        embedding = self.embedder.embed_chunk(chunk)

        self.collection.add(
            ids=[chunk.id],
            embeddings=[embedding],
            documents=[chunk.content],
            metadatas=[chunk.metadata],
        )

    def add_chunks(self, chunks: list[CodeChunk], batch_size: int = 100) -> int:
        """Add multiple chunks to the store in batches."""
        total_added = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            ids = [chunk.id for chunk in batch]
            embeddings = self.embedder.embed_chunks(batch)
            documents = [chunk.content for chunk in batch]
            metadatas = [chunk.metadata for chunk in batch]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            total_added += len(batch)

        return total_added

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Search for relevant code chunks.

        Args:
            query: Search query text
            n_results: Number of results to return
            where: Optional filter dict (e.g., {"language": "python"})

        Returns:
            List of results with content, metadata, and distance
        """
        query_embedding = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "relevance": 1 - results["distances"][0][i],  # Convert distance to similarity
            })

        return formatted

    def search_by_file(self, file_path: str) -> list[dict]:
        """Get all chunks from a specific file."""
        results = self.collection.get(
            where={"file_path": file_path},
            include=["documents", "metadatas"],
        )

        formatted = []
        for i in range(len(results["ids"])):
            formatted.append({
                "id": results["ids"][i],
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
            })

        return formatted

    def delete_file(self, file_path: str) -> int:
        """Delete all chunks from a specific file."""
        existing = self.collection.get(where={"file_path": file_path})
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])
        return len(existing["ids"])

    def clear(self) -> None:
        """Clear all data from the collection."""
        self.client.delete_collection(self.collection_name)
        self._collection = None

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count(),
            "persist_dir": str(self.persist_dir),
        }


def index_codebase(
    root_dir: str | Path,
    collection_name: str = "codebase",
    persist_dir: Optional[Path] = None,
    show_progress: bool = True,
) -> dict:
    """Index a codebase into the vector store.

    Args:
        root_dir: Root directory of the codebase
        collection_name: Name for the ChromaDB collection
        persist_dir: Directory to persist the vector store
        show_progress: Whether to show progress output

    Returns:
        Statistics about the indexed codebase
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    loader = FileLoader(root_dir)
    store = VectorStore(collection_name, persist_dir)

    # Clear existing data
    try:
        store.clear()
    except Exception:
        pass  # Collection might not exist

    # Recreate store after clear
    store = VectorStore(collection_name, persist_dir)

    # Collect chunks
    chunks = list(loader.load_chunks())

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task(f"Indexing {len(chunks)} chunks...", total=None)
            total_added = store.add_chunks(chunks)
            progress.update(task, description=f"Indexed {total_added} chunks")
    else:
        total_added = store.add_chunks(chunks)

    return {
        **loader.get_stats(),
        "chunks_indexed": total_added,
        "persist_dir": str(store.persist_dir),
    }

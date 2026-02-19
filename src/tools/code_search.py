"""RAG-powered code search tools."""

from typing import Optional

from langchain_core.tools import tool

from ..indexer.vector_store import VectorStore


# Global vector store instance (initialized when codebase is indexed)
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> Optional[VectorStore]:
    """Get the global vector store instance."""
    return _vector_store


def set_vector_store(store: VectorStore) -> None:
    """Set the global vector store instance."""
    global _vector_store
    _vector_store = store


def init_vector_store(collection_name: str = "codebase") -> VectorStore:
    """Initialize the vector store."""
    global _vector_store
    _vector_store = VectorStore(collection_name)
    return _vector_store


@tool
def search_codebase(
    query: str,
    n_results: int = 5,
    language: Optional[str] = None,
) -> str:
    """Search the codebase for relevant code using semantic search.

    Args:
        query: Natural language description of what you're looking for
        n_results: Number of results to return (default: 5)
        language: Optional filter by programming language (e.g., "python", "javascript")

    Returns:
        Relevant code snippets with file paths and line numbers
    """
    store = get_vector_store()

    if store is None:
        return "Error: Codebase not indexed. Run 'index' command first."

    # Build filter if language specified
    where = {"language": language} if language else None

    try:
        results = store.search(query, n_results=n_results, where=where)

        if not results:
            return f"No results found for query: {query}"

        # Format results
        output = []
        for i, result in enumerate(results, 1):
            meta = result["metadata"]
            relevance = result["relevance"]

            output.append(
                f"--- Result {i} (relevance: {relevance:.2f}) ---\n"
                f"File: {meta['file_path']} (lines {meta['start_line']}-{meta['end_line']})\n"
                f"Language: {meta['language']}\n"
                f"```{meta['language']}\n{result['content']}\n```\n"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error searching codebase: {str(e)}"


@tool
def find_similar_code(file_path: str, start_line: int, end_line: int, n_results: int = 5) -> str:
    """Find code similar to a specific section of a file.

    Args:
        file_path: Path to the reference file
        start_line: Starting line of the code section
        end_line: Ending line of the code section
        n_results: Number of similar results to return

    Returns:
        Similar code snippets from other parts of the codebase
    """
    store = get_vector_store()

    if store is None:
        return "Error: Codebase not indexed. Run 'index' command first."

    try:
        # Read the reference code
        from pathlib import Path

        path = Path(file_path).resolve()
        if not path.exists():
            return f"Error: File not found: {file_path}"

        lines = path.read_text().split("\n")
        reference_code = "\n".join(lines[start_line - 1 : end_line])

        if not reference_code.strip():
            return "Error: Selected line range is empty"

        # Search for similar code
        results = store.search(reference_code, n_results=n_results + 1)  # +1 to exclude self

        # Filter out the reference code itself
        filtered = [r for r in results if r["metadata"]["file_path"] != file_path][:n_results]

        if not filtered:
            return "No similar code found in the codebase."

        # Format results
        output = [f"Code similar to {file_path}:{start_line}-{end_line}:\n"]
        for i, result in enumerate(filtered, 1):
            meta = result["metadata"]
            relevance = result["relevance"]

            output.append(
                f"--- Similar {i} (similarity: {relevance:.2f}) ---\n"
                f"File: {meta['file_path']} (lines {meta['start_line']}-{meta['end_line']})\n"
                f"```{meta['language']}\n{result['content']}\n```\n"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error finding similar code: {str(e)}"


@tool
def get_file_chunks(file_path: str) -> str:
    """Get all indexed chunks for a specific file.

    Args:
        file_path: Path to the file

    Returns:
        All indexed chunks from the file
    """
    store = get_vector_store()

    if store is None:
        return "Error: Codebase not indexed. Run 'index' command first."

    try:
        results = store.search_by_file(file_path)

        if not results:
            return f"No indexed chunks found for file: {file_path}"

        # Sort by line number
        results.sort(key=lambda x: x["metadata"]["start_line"])

        output = [f"Indexed chunks for {file_path}:\n"]
        for result in results:
            meta = result["metadata"]
            output.append(
                f"Lines {meta['start_line']}-{meta['end_line']}:\n"
                f"```{meta['language']}\n{result['content']}\n```\n"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error getting file chunks: {str(e)}"

"""File loader for reading and chunking code files."""

import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

from ..config import get_config


@dataclass
class CodeChunk:
    """A chunk of code with metadata."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    chunk_index: int

    @property
    def metadata(self) -> dict:
        """Return metadata dict for vector store."""
        return {
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "chunk_index": self.chunk_index,
        }

    @property
    def id(self) -> str:
        """Generate unique ID for this chunk."""
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


# Language detection based on file extension
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".bash": "bash",
}


class FileLoader:
    """Loads and chunks code files from a directory."""

    def __init__(
        self,
        root_dir: str | Path,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.root_dir = Path(root_dir).resolve()
        config = get_config()
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.supported_extensions = config.supported_extensions
        self.ignore_dirs = config.ignore_dirs

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        for pattern in self.ignore_dirs:
            if fnmatch.fnmatch(path.name, pattern):
                return True
            # Check parent directories too
            for parent in path.parents:
                if fnmatch.fnmatch(parent.name, pattern):
                    return True
        return False

    def _get_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        return EXTENSION_TO_LANGUAGE.get(file_path.suffix.lower(), "text")

    def _chunk_content(
        self,
        content: str,
        file_path: Path,
        language: str,
    ) -> Generator[CodeChunk, None, None]:
        """Split content into overlapping chunks."""
        lines = content.split("\n")
        total_lines = len(lines)

        if total_lines == 0:
            return

        # Calculate approximate lines per chunk
        avg_line_length = len(content) / max(total_lines, 1)
        lines_per_chunk = max(1, int(self.chunk_size / max(avg_line_length, 1)))
        overlap_lines = max(0, int(self.chunk_overlap / max(avg_line_length, 1)))

        chunk_index = 0
        start_line = 0

        while start_line < total_lines:
            end_line = min(start_line + lines_per_chunk, total_lines)
            chunk_content = "\n".join(lines[start_line:end_line])

            # Skip empty chunks
            if chunk_content.strip():
                yield CodeChunk(
                    content=chunk_content,
                    file_path=str(file_path),
                    start_line=start_line + 1,  # 1-indexed
                    end_line=end_line,
                    language=language,
                    chunk_index=chunk_index,
                )
                chunk_index += 1

            # Move to next chunk with overlap
            start_line = end_line - overlap_lines
            if start_line >= end_line:
                start_line = end_line

    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection."""
        encodings = ["utf-8", "latin-1", "cp1252"]
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return None

    def iter_files(self) -> Generator[Path, None, None]:
        """Iterate over all supported files in the directory."""
        for path in self.root_dir.rglob("*"):
            if path.is_file() and not self._should_ignore(path):
                if path.suffix.lower() in self.supported_extensions:
                    yield path

    def load_chunks(self) -> Generator[CodeChunk, None, None]:
        """Load and chunk all files in the directory."""
        for file_path in self.iter_files():
            content = self._read_file(file_path)
            if content is None:
                continue

            relative_path = file_path.relative_to(self.root_dir)
            language = self._get_language(file_path)

            yield from self._chunk_content(content, relative_path, language)

    def load_file(self, file_path: str | Path) -> list[CodeChunk]:
        """Load and chunk a single file."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.root_dir / path

        content = self._read_file(path)
        if content is None:
            return []

        relative_path = path.relative_to(self.root_dir) if self.root_dir in path.parents else path
        language = self._get_language(path)

        return list(self._chunk_content(content, relative_path, language))

    def get_stats(self) -> dict:
        """Get statistics about the codebase."""
        stats = {
            "total_files": 0,
            "total_chunks": 0,
            "by_language": {},
        }

        for chunk in self.load_chunks():
            stats["total_chunks"] += 1

            # Track unique files
            if chunk.chunk_index == 0:
                stats["total_files"] += 1

            # Track by language
            lang = chunk.language
            if lang not in stats["by_language"]:
                stats["by_language"][lang] = {"files": 0, "chunks": 0}
            if chunk.chunk_index == 0:
                stats["by_language"][lang]["files"] += 1
            stats["by_language"][lang]["chunks"] += 1

        return stats

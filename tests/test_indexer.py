"""Tests for the indexer module."""

import tempfile
from pathlib import Path

import pytest

from src.indexer.file_loader import FileLoader, CodeChunk


class TestFileLoader:
    """Tests for FileLoader class."""

    def test_code_chunk_metadata(self):
        """Test CodeChunk metadata generation."""
        chunk = CodeChunk(
            content="def hello(): pass",
            file_path="test.py",
            start_line=1,
            end_line=1,
            language="python",
            chunk_index=0,
        )

        metadata = chunk.metadata
        assert metadata["file_path"] == "test.py"
        assert metadata["language"] == "python"
        assert metadata["start_line"] == 1

    def test_code_chunk_id(self):
        """Test CodeChunk ID generation."""
        chunk = CodeChunk(
            content="def hello(): pass",
            file_path="src/main.py",
            start_line=10,
            end_line=20,
            language="python",
            chunk_index=0,
        )

        assert chunk.id == "src/main.py:10-20"

    def test_file_loader_iter_files(self):
        """Test file iteration in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "test.py").write_text("print('hello')")
            (Path(tmpdir) / "test.js").write_text("console.log('hello')")
            (Path(tmpdir) / "ignored.exe").write_text("binary")

            loader = FileLoader(tmpdir)
            files = list(loader.iter_files())

            # Should find .py and .js but not .exe
            assert len(files) == 2
            extensions = {f.suffix for f in files}
            assert ".py" in extensions
            assert ".js" in extensions

    def test_file_loader_chunks(self):
        """Test file chunking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file with multiple lines
            content = "\n".join([f"line {i}" for i in range(100)])
            (Path(tmpdir) / "test.py").write_text(content)

            loader = FileLoader(tmpdir, chunk_size=200, chunk_overlap=50)
            chunks = list(loader.load_chunks())

            # Should produce multiple chunks
            assert len(chunks) > 1

            # All chunks should be from test.py
            for chunk in chunks:
                assert chunk.file_path == "test.py"
                assert chunk.language == "python"

    def test_file_loader_ignores_dirs(self):
        """Test that ignored directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in regular and ignored directories
            (Path(tmpdir) / "regular.py").write_text("code")
            (Path(tmpdir) / "node_modules").mkdir()
            (Path(tmpdir) / "node_modules" / "dep.js").write_text("dependency")

            loader = FileLoader(tmpdir)
            files = list(loader.iter_files())

            # Should only find regular.py, not the file in node_modules
            assert len(files) == 1
            assert files[0].name == "regular.py"

    def test_file_loader_stats(self):
        """Test statistics generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test1.py").write_text("print(1)")
            (Path(tmpdir) / "test2.py").write_text("print(2)")
            (Path(tmpdir) / "test.js").write_text("console.log(1)")

            loader = FileLoader(tmpdir)
            stats = loader.get_stats()

            assert stats["total_files"] == 3
            assert "python" in stats["by_language"]
            assert "javascript" in stats["by_language"]


class TestCodeChunk:
    """Additional tests for CodeChunk."""

    def test_empty_content_handling(self):
        """Test handling of empty content."""
        chunk = CodeChunk(
            content="",
            file_path="empty.py",
            start_line=1,
            end_line=1,
            language="python",
            chunk_index=0,
        )

        assert chunk.content == ""
        assert chunk.id == "empty.py:1-1"

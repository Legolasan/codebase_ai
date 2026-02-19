"""File operation tools for agents."""

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from ..config import get_config, PermissionMode


def _check_write_permission() -> bool:
    """Check if write operations are allowed."""
    config = get_config()
    if config.permission_mode == PermissionMode.READ_ONLY:
        return False
    return True


@tool
def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read contents of a file.

    Args:
        file_path: Path to the file to read
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (1-indexed)

    Returns:
        File contents as a string, or error message
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        content = path.read_text(encoding="utf-8")

        # Handle line range if specified
        if start_line is not None or end_line is not None:
            lines = content.split("\n")
            start = (start_line or 1) - 1  # Convert to 0-indexed
            end = end_line or len(lines)
            content = "\n".join(lines[start:end])

        return content

    except UnicodeDecodeError:
        return f"Error: Unable to decode file (not UTF-8): {file_path}"
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str, create_dirs: bool = True) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories if they don't exist

    Returns:
        Success message or error
    """
    if not _check_write_permission():
        return "Error: Write operations are disabled in read-only mode"

    config = get_config()
    if config.permission_mode == PermissionMode.ASK_BEFORE:
        # In a real implementation, this would prompt the user
        # For now, we'll include this info in the return
        return f"PERMISSION_REQUIRED: Write to {file_path}\nContent preview:\n{content[:500]}..."

    try:
        path = Path(file_path).resolve()

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {file_path}"

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False,
    include_hidden: bool = False,
) -> str:
    """List files in a directory.

    Args:
        directory: Path to the directory
        pattern: Glob pattern to filter files (default: "*")
        recursive: Whether to search recursively
        include_hidden: Whether to include hidden files (starting with .)

    Returns:
        List of file paths, one per line
    """
    try:
        path = Path(directory).resolve()

        if not path.exists():
            return f"Error: Directory not found: {directory}"

        if not path.is_dir():
            return f"Error: Not a directory: {directory}"

        # Get matching files
        if recursive:
            files = path.rglob(pattern)
        else:
            files = path.glob(pattern)

        # Filter and format results
        results = []
        for f in sorted(files):
            if f.is_file():
                if not include_hidden and f.name.startswith("."):
                    continue
                # Make path relative to the directory
                try:
                    rel_path = f.relative_to(path)
                    results.append(str(rel_path))
                except ValueError:
                    results.append(str(f))

        if not results:
            return f"No files found matching pattern '{pattern}' in {directory}"

        return "\n".join(results)

    except PermissionError:
        return f"Error: Permission denied: {directory}"
    except Exception as e:
        return f"Error listing files: {str(e)}"


@tool
def file_info(file_path: str) -> str:
    """Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        File information including size, modification time, etc.
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return f"Error: File not found: {file_path}"

        stat = path.stat()
        from datetime import datetime

        info = {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": stat.st_size,
            "size_human": _human_readable_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

        return "\n".join(f"{k}: {v}" for k, v in info.items())

    except Exception as e:
        return f"Error getting file info: {str(e)}"


def _human_readable_size(size: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

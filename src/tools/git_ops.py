"""Git operation tools."""

from typing import Optional

from langchain_core.tools import tool

from ..config import get_config, PermissionMode
from .shell import run_command


@tool
def git_status() -> str:
    """Get the current git status.

    Returns:
        Git status output showing staged, unstaged, and untracked files
    """
    return run_command.invoke({"command": "git status"})


@tool
def git_diff(
    file_path: Optional[str] = None,
    staged: bool = False,
    commit: Optional[str] = None,
) -> str:
    """Show git diff for changes.

    Args:
        file_path: Optional specific file to diff
        staged: Whether to show staged changes (--cached)
        commit: Optional commit hash to diff against

    Returns:
        Git diff output
    """
    cmd = "git diff"

    if staged:
        cmd += " --cached"

    if commit:
        cmd += f" {commit}"

    if file_path:
        cmd += f" -- {file_path}"

    return run_command.invoke({"command": cmd})


@tool
def git_log(
    n: int = 10,
    oneline: bool = True,
    file_path: Optional[str] = None,
) -> str:
    """Show git commit history.

    Args:
        n: Number of commits to show (default: 10)
        oneline: Whether to show one line per commit
        file_path: Optional file to show history for

    Returns:
        Git log output
    """
    cmd = f"git log -n {n}"

    if oneline:
        cmd += " --oneline"

    if file_path:
        cmd += f" -- {file_path}"

    return run_command.invoke({"command": cmd})


@tool
def git_show(commit: str, file_path: Optional[str] = None) -> str:
    """Show details of a specific commit.

    Args:
        commit: Commit hash or reference (e.g., HEAD, HEAD~1)
        file_path: Optional specific file to show from commit

    Returns:
        Commit details and diff
    """
    cmd = f"git show {commit}"

    if file_path:
        cmd += f" -- {file_path}"

    return run_command.invoke({"command": cmd})


@tool
def git_blame(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Show git blame for a file.

    Args:
        file_path: Path to the file
        start_line: Optional starting line number
        end_line: Optional ending line number

    Returns:
        Git blame output showing who changed each line
    """
    cmd = f"git blame {file_path}"

    if start_line and end_line:
        cmd += f" -L {start_line},{end_line}"

    return run_command.invoke({"command": cmd})


@tool
def git_branch(show_all: bool = False) -> str:
    """List git branches.

    Args:
        show_all: Whether to show remote branches too

    Returns:
        List of branches
    """
    cmd = "git branch"
    if show_all:
        cmd += " -a"

    return run_command.invoke({"command": cmd})


@tool
def git_commit(message: str, add_all: bool = False) -> str:
    """Create a git commit.

    Args:
        message: Commit message
        add_all: Whether to stage all changes before committing

    Returns:
        Commit result
    """
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        return "Error: Git commits are disabled in read-only mode."

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        return f"PERMISSION_REQUIRED: Create git commit with message: {message}"

    if add_all:
        add_result = run_command.invoke({"command": "git add -A"})
        if "Error" in add_result:
            return add_result

    # Use a properly escaped commit message
    import shlex
    safe_message = shlex.quote(message)
    cmd = f"git commit -m {safe_message}"

    return run_command.invoke({"command": cmd})


@tool
def git_add(file_paths: str) -> str:
    """Stage files for commit.

    Args:
        file_paths: Space-separated list of file paths to stage, or "." for all

    Returns:
        Result of git add
    """
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        return "Error: Git staging is disabled in read-only mode."

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        return f"PERMISSION_REQUIRED: Stage files: {file_paths}"

    return run_command.invoke({"command": f"git add {file_paths}"})


@tool
def git_checkout(target: str, create_branch: bool = False) -> str:
    """Checkout a branch or commit.

    Args:
        target: Branch name or commit hash
        create_branch: Whether to create a new branch

    Returns:
        Checkout result
    """
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        return "Error: Git checkout is disabled in read-only mode."

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        action = "Create and checkout" if create_branch else "Checkout"
        return f"PERMISSION_REQUIRED: {action} branch: {target}"

    cmd = "git checkout"
    if create_branch:
        cmd += " -b"
    cmd += f" {target}"

    return run_command.invoke({"command": cmd})

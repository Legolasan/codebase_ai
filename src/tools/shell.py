"""Shell command execution tools."""

import subprocess
import shlex
from typing import Optional

from langchain_core.tools import tool

from ..config import get_config, PermissionMode


# Commands that are always allowed (safe/read-only)
SAFE_COMMANDS = {
    "ls", "dir", "pwd", "echo", "cat", "head", "tail", "grep", "find",
    "wc", "sort", "uniq", "diff", "which", "whereis", "file", "tree",
    "python --version", "node --version", "npm --version", "pip --version",
    "git status", "git log", "git diff", "git branch", "git show",
}

# Commands that are never allowed (dangerous)
BLOCKED_COMMANDS = {
    "rm -rf /", "rm -rf /*", ":(){ :|:& };:", "mkfs", "dd if=/dev/",
    "> /dev/sda", "chmod -R 777 /", "chown -R",
}


def _is_safe_command(command: str) -> bool:
    """Check if a command is in the safe list."""
    cmd_lower = command.lower().strip()
    for safe in SAFE_COMMANDS:
        if cmd_lower.startswith(safe):
            return True
    return False


def _is_blocked_command(command: str) -> bool:
    """Check if a command is blocked."""
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return True
    return False


@tool
def run_command(
    command: str,
    working_dir: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """Execute a shell command.

    Args:
        command: The shell command to execute
        working_dir: Optional working directory for the command
        timeout: Maximum execution time in seconds (default: 60)

    Returns:
        Command output (stdout and stderr combined) or error message
    """
    # Check for blocked commands
    if _is_blocked_command(command):
        return "Error: This command is blocked for security reasons."

    # Check permissions
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        if not _is_safe_command(command):
            return (
                "Error: Only read-only commands are allowed in read-only mode.\n"
                f"Command '{command}' may modify the system."
            )

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        if not _is_safe_command(command):
            return f"PERMISSION_REQUIRED: Execute command: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- STDERR ---\n"
            output += result.stderr

        if result.returncode != 0:
            output += f"\n(Exit code: {result.returncode})"

        return output if output else "(No output)"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def run_python(code: str, timeout: int = 30) -> str:
    """Execute Python code and return the result.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 30)

    Returns:
        Code output or error message
    """
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        return "Error: Code execution is disabled in read-only mode."

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        return f"PERMISSION_REQUIRED: Execute Python code:\n```python\n{code}\n```"

    try:
        # Write code to a temp file and execute
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n--- STDERR ---\n"
                output += result.stderr

            if result.returncode != 0:
                output += f"\n(Exit code: {result.returncode})"

            return output if output else "(No output)"

        finally:
            os.unlink(temp_file)

    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing code: {str(e)}"


@tool
def run_tests(
    test_path: Optional[str] = None,
    framework: str = "pytest",
    verbose: bool = True,
) -> str:
    """Run tests using the specified test framework.

    Args:
        test_path: Path to test file or directory (default: current directory)
        framework: Test framework to use ("pytest", "unittest", "jest", "mocha")
        verbose: Whether to show verbose output

    Returns:
        Test results
    """
    config = get_config()

    if config.permission_mode == PermissionMode.READ_ONLY:
        return "Error: Test execution is disabled in read-only mode."

    commands = {
        "pytest": f"pytest {'-v' if verbose else ''} {test_path or '.'}",
        "unittest": f"python -m unittest {'discover' if not test_path else test_path} {'-v' if verbose else ''}",
        "jest": f"npx jest {test_path or ''} {'--verbose' if verbose else ''}",
        "mocha": f"npx mocha {test_path or 'test/'} {'--reporter spec' if verbose else ''}",
    }

    if framework not in commands:
        return f"Error: Unknown test framework '{framework}'. Supported: {list(commands.keys())}"

    command = commands[framework]

    if config.permission_mode == PermissionMode.ASK_BEFORE:
        return f"PERMISSION_REQUIRED: Run tests: {command}"

    return run_command.invoke({"command": command, "timeout": 300})

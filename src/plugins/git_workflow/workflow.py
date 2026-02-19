"""Git workflow utilities for branching and commits.

Provides functions to enforce proper git branching workflow
before making code changes.
"""

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class BranchType(Enum):
    """Types of branches in the workflow."""
    FEATURE = "feature"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"


@dataclass
class GitStatus:
    """Status of the git repository."""
    is_git_repo: bool
    current_branch: Optional[str] = None
    is_clean: bool = True
    has_staged: bool = False
    has_unstaged: bool = False
    has_untracked: bool = False
    error: Optional[str] = None


@dataclass
class BranchResult:
    """Result of a branch operation."""
    success: bool
    branch_name: Optional[str] = None
    message: str = ""
    was_created: bool = False


def run_git_command(args: list[str]) -> Tuple[bool, str]:
    """Run a git command and return (success, output).

    Args:
        args: List of command arguments (without 'git' prefix)

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except FileNotFoundError:
        return False, "Git is not installed"
    except Exception as e:
        return False, str(e)


def is_git_repo() -> bool:
    """Check if the current directory is a git repository."""
    success, _ = run_git_command(["rev-parse", "--git-dir"])
    return success


def get_git_status() -> GitStatus:
    """Get comprehensive git status.

    Returns:
        GitStatus object with repository state
    """
    # Check if it's a git repo
    if not is_git_repo():
        return GitStatus(
            is_git_repo=False,
            error="Not a git repository"
        )

    # Get current branch
    success, branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    if not success:
        return GitStatus(
            is_git_repo=True,
            error=f"Could not get current branch: {branch}"
        )

    # Get porcelain status for cleanliness check
    success, status_output = run_git_command(["status", "--porcelain"])

    has_staged = False
    has_unstaged = False
    has_untracked = False

    if success and status_output:
        for line in status_output.split("\n"):
            if not line:
                continue
            index_status = line[0] if len(line) > 0 else " "
            work_status = line[1] if len(line) > 1 else " "

            if index_status != " " and index_status != "?":
                has_staged = True
            if work_status != " " and work_status != "?":
                has_unstaged = True
            if index_status == "?" or work_status == "?":
                has_untracked = True

    return GitStatus(
        is_git_repo=True,
        current_branch=branch,
        is_clean=not (has_staged or has_unstaged or has_untracked),
        has_staged=has_staged,
        has_unstaged=has_unstaged,
        has_untracked=has_untracked,
    )


def get_current_branch() -> Optional[str]:
    """Get the current branch name.

    Returns:
        Branch name or None if not in a git repo
    """
    success, branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return branch if success else None


def is_feature_branch(branch_name: str) -> bool:
    """Check if a branch name follows the feature branch convention.

    Valid prefixes: feature/, fix/, refactor/, docs/

    Args:
        branch_name: Name of the branch to check

    Returns:
        True if it's a properly named feature branch
    """
    valid_prefixes = ["feature/", "fix/", "refactor/", "docs/"]
    return any(branch_name.startswith(prefix) for prefix in valid_prefixes)


def slugify(text: str) -> str:
    """Convert text to a slug suitable for branch names.

    Args:
        text: Text to convert

    Returns:
        Slugified string
    """
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove any characters that aren't alphanumeric or hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Trim hyphens from ends
    slug = slug.strip("-")
    # Limit length
    return slug[:50]


def generate_branch_name(description: str, branch_type: BranchType = BranchType.FEATURE) -> str:
    """Generate a branch name from a description.

    Args:
        description: Description of the work to be done
        branch_type: Type of branch (feature, fix, refactor, docs)

    Returns:
        Generated branch name
    """
    slug = slugify(description)
    return f"{branch_type.value}/{slug}"


def create_branch(branch_name: str, checkout: bool = True) -> BranchResult:
    """Create a new branch.

    Args:
        branch_name: Name of the branch to create
        checkout: Whether to checkout the branch after creating

    Returns:
        BranchResult with operation status
    """
    # Check if branch already exists
    success, _ = run_git_command(["rev-parse", "--verify", branch_name])
    if success:
        # Branch exists, just checkout if requested
        if checkout:
            success, output = run_git_command(["checkout", branch_name])
            if success:
                return BranchResult(
                    success=True,
                    branch_name=branch_name,
                    message=f"Switched to existing branch '{branch_name}'",
                    was_created=False,
                )
            else:
                return BranchResult(
                    success=False,
                    branch_name=branch_name,
                    message=f"Failed to checkout branch: {output}",
                )
        else:
            return BranchResult(
                success=True,
                branch_name=branch_name,
                message=f"Branch '{branch_name}' already exists",
                was_created=False,
            )

    # Create the branch
    if checkout:
        success, output = run_git_command(["checkout", "-b", branch_name])
    else:
        success, output = run_git_command(["branch", branch_name])

    if success:
        return BranchResult(
            success=True,
            branch_name=branch_name,
            message=f"Created and switched to branch '{branch_name}'" if checkout else f"Created branch '{branch_name}'",
            was_created=True,
        )
    else:
        return BranchResult(
            success=False,
            branch_name=branch_name,
            message=f"Failed to create branch: {output}",
        )


def ensure_feature_branch(
    task_description: str,
    branch_type: BranchType = BranchType.FEATURE,
    auto_create: bool = True,
) -> BranchResult:
    """Ensure we're on a feature branch before making changes.

    This is the main entry point for the workflow. It:
    1. Checks if we're in a git repo
    2. Checks if we're already on a feature branch
    3. Creates and switches to a new feature branch if needed

    Args:
        task_description: Description of the task (used for branch naming)
        branch_type: Type of branch to create
        auto_create: Whether to automatically create a branch if not on one

    Returns:
        BranchResult with the outcome
    """
    status = get_git_status()

    # Not a git repo
    if not status.is_git_repo:
        return BranchResult(
            success=False,
            message="Not a git repository. Initialize with 'git init' first.",
        )

    current_branch = status.current_branch

    # Already on a feature branch
    if current_branch and is_feature_branch(current_branch):
        return BranchResult(
            success=True,
            branch_name=current_branch,
            message=f"Already on feature branch '{current_branch}'",
            was_created=False,
        )

    # On main/master or other branch - need to create feature branch
    if not auto_create:
        return BranchResult(
            success=False,
            branch_name=current_branch,
            message=f"On branch '{current_branch}'. Create a feature branch first.",
        )

    # Generate and create feature branch
    new_branch = generate_branch_name(task_description, branch_type)
    return create_branch(new_branch, checkout=True)


def infer_branch_type(task_description: str) -> BranchType:
    """Infer the branch type from the task description.

    Args:
        task_description: Description of the task

    Returns:
        Inferred BranchType
    """
    desc_lower = task_description.lower()

    # Check for fix-related keywords
    fix_keywords = ["fix", "bug", "error", "issue", "patch", "resolve", "repair"]
    if any(keyword in desc_lower for keyword in fix_keywords):
        return BranchType.FIX

    # Check for refactor-related keywords
    refactor_keywords = ["refactor", "restructure", "reorganize", "cleanup", "clean up", "improve"]
    if any(keyword in desc_lower for keyword in refactor_keywords):
        return BranchType.REFACTOR

    # Check for docs-related keywords
    docs_keywords = ["document", "docs", "readme", "comment", "docstring"]
    if any(keyword in desc_lower for keyword in docs_keywords):
        return BranchType.DOCS

    # Default to feature
    return BranchType.FEATURE


def prepare_for_implementation(task_description: str) -> BranchResult:
    """Prepare the git environment for implementing changes.

    This is a convenience function that:
    1. Infers the branch type from the task description
    2. Ensures we're on a properly named feature branch

    Args:
        task_description: Description of what will be implemented

    Returns:
        BranchResult with the preparation outcome
    """
    branch_type = infer_branch_type(task_description)
    return ensure_feature_branch(task_description, branch_type, auto_create=True)

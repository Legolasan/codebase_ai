"""Git workflow plugin for enforcing branching practices.

This plugin ensures proper git branching workflow is followed
when making code changes through the coding assistant.
"""

import logging
from typing import Any, Callable, Optional

from langchain_core.tools import tool

from ..base import BasePlugin
from .workflow import (
    BranchType,
    BranchResult,
    GitStatus,
    get_git_status,
    get_current_branch,
    is_feature_branch,
    ensure_feature_branch,
    prepare_for_implementation,
    create_branch,
    generate_branch_name,
    infer_branch_type,
)

logger = logging.getLogger(__name__)


class GitWorkflowPlugin(BasePlugin):
    """Plugin for enforcing git branching workflow.

    This plugin provides:
    - Git status checking tools
    - Feature branch creation and management
    - Workflow enforcement before implementations

    When enabled, the implementation agent will automatically
    create feature branches before making changes.

    Usage:
        # Enable the plugin
        assistant plugins enable git_workflow

        # Check status
        assistant git status

        # Create a feature branch manually
        assistant git branch "add user authentication"

        # The plugin will auto-create branches during implementations
        assistant implement "add login page"
        # -> Automatically creates feature/add-login-page branch
    """

    name = "git_workflow"
    description = "Enforces git branching workflow for code changes"
    version = "1.0.0"
    dependencies = []

    def __init__(self):
        super().__init__()
        self.auto_branch = True  # Automatically create branches
        self.require_feature_branch = True  # Require feature branch for changes

    def setup(self) -> None:
        """Initialize the plugin."""
        logger.info("Git workflow plugin initialized")

    def teardown(self) -> None:
        """Cleanup the plugin."""
        pass

    def get_tools(self) -> list:
        """Return LangChain tools for git workflow."""
        return [
            git_workflow_status,
            git_workflow_create_branch,
            git_workflow_prepare,
        ]

    def get_commands(self) -> list[Callable]:
        """Return CLI commands."""
        return []

    def prepare_for_changes(self, task_description: str) -> BranchResult:
        """Prepare git environment before making changes.

        This is called by the implementation agent before modifying code.

        Args:
            task_description: Description of the changes to be made

        Returns:
            BranchResult with preparation status
        """
        if not self.auto_branch:
            # Just check current status
            status = get_git_status()
            if not status.is_git_repo:
                return BranchResult(
                    success=False,
                    message="Not a git repository"
                )
            return BranchResult(
                success=True,
                branch_name=status.current_branch,
                message=f"On branch '{status.current_branch}'"
            )

        return prepare_for_implementation(task_description)

    def check_can_implement(self) -> tuple[bool, str]:
        """Check if implementation is allowed.

        Returns:
            Tuple of (can_implement, message)
        """
        status = get_git_status()

        if not status.is_git_repo:
            if self.require_feature_branch:
                return False, "Not a git repository. Initialize with 'git init' first."
            return True, "Warning: Not a git repository - changes won't be tracked."

        if self.require_feature_branch:
            if not is_feature_branch(status.current_branch or ""):
                return False, f"On branch '{status.current_branch}'. Please switch to a feature branch first."

        return True, f"Ready to implement on branch '{status.current_branch}'"

    def get_workflow_info(self) -> dict:
        """Get current workflow configuration and status."""
        status = get_git_status()

        return {
            "is_git_repo": status.is_git_repo,
            "current_branch": status.current_branch,
            "is_feature_branch": is_feature_branch(status.current_branch or "") if status.current_branch else False,
            "is_clean": status.is_clean,
            "auto_branch": self.auto_branch,
            "require_feature_branch": self.require_feature_branch,
        }


# =============================================================================
# LangChain Tools
# =============================================================================


@tool
def git_workflow_status() -> str:
    """Get git workflow status for the current directory.

    Returns comprehensive information about:
    - Whether this is a git repository
    - Current branch name
    - Whether on a feature branch
    - Working directory cleanliness

    Returns:
        Formatted status string
    """
    status = get_git_status()

    if not status.is_git_repo:
        return """Git Workflow Status:
- Not a git repository
- Run 'git init' to initialize

Tip: Initialize git before making changes to track your work."""

    on_feature = is_feature_branch(status.current_branch or "")
    branch_status = "Feature branch" if on_feature else "Non-feature branch"

    clean_status = "Clean" if status.is_clean else "Has changes"
    changes = []
    if status.has_staged:
        changes.append("staged")
    if status.has_unstaged:
        changes.append("unstaged")
    if status.has_untracked:
        changes.append("untracked")

    change_details = f" ({', '.join(changes)})" if changes else ""

    return f"""Git Workflow Status:
- Repository: Yes
- Current branch: {status.current_branch}
- Branch type: {branch_status}
- Working directory: {clean_status}{change_details}

{"Ready for implementation!" if on_feature else "Create a feature branch before making changes."}"""


@tool
def git_workflow_create_branch(description: str, branch_type: str = "auto") -> str:
    """Create a feature branch for implementation work.

    Creates a properly named branch following the convention:
    - feature/<name> for new features
    - fix/<name> for bug fixes
    - refactor/<name> for refactoring
    - docs/<name> for documentation

    Args:
        description: Description of the work (used to generate branch name)
        branch_type: Type of branch: feature, fix, refactor, docs, or auto (inferred)

    Returns:
        Result of branch creation
    """
    # Map string to BranchType
    if branch_type == "auto":
        b_type = infer_branch_type(description)
    else:
        try:
            b_type = BranchType(branch_type.lower())
        except ValueError:
            return f"Invalid branch type: {branch_type}. Use: feature, fix, refactor, docs, or auto"

    result = ensure_feature_branch(description, b_type, auto_create=True)

    if result.success:
        emoji = "" if not result.was_created else ""
        return f"""{emoji} {result.message}

Branch: {result.branch_name}
Type: {b_type.value}

You're now ready to make changes!"""
    else:
        return f"Failed to create branch: {result.message}"


@tool
def git_workflow_prepare(task_description: str) -> str:
    """Prepare git environment for implementing changes.

    This tool should be called before making any code changes.
    It will:
    1. Check if we're in a git repository
    2. Create a feature branch if not already on one
    3. Report the current status

    Args:
        task_description: What you're about to implement

    Returns:
        Preparation status and instructions
    """
    result = prepare_for_implementation(task_description)

    if result.success:
        action = "Created new branch" if result.was_created else "Using existing branch"
        return f"""Git Workflow Ready

{action}: {result.branch_name}

You can now make your changes. When done:
1. Review changes: git diff
2. Stage files: git add <files>
3. Commit: git commit -m "Your message"
"""
    else:
        return f"""Git Workflow Issue

{result.message}

Before implementing:
1. Initialize git: git init
2. Or switch to a feature branch: git checkout -b feature/your-feature
"""

"""Git workflow plugin for enforcing branching practices.

This plugin ensures proper git branching workflow is followed
when making code changes through the coding assistant.

Features:
- Automatic feature branch creation
- Branch naming conventions (feature/, fix/, refactor/, docs/)
- Workflow status checking
- Integration with implementation agent

Usage:
    # Enable the plugin
    assistant plugins enable git_workflow

    # Check git workflow status
    assistant git status

    # Manually create a feature branch
    assistant git branch "add user authentication"

    # Implementation commands auto-create branches
    assistant implement "add login page"
    # -> Creates feature/add-login-page and switches to it
"""

from .plugin import GitWorkflowPlugin
from .workflow import (
    BranchType,
    BranchResult,
    GitStatus,
    get_git_status,
    get_current_branch,
    is_git_repo,
    is_feature_branch,
    ensure_feature_branch,
    prepare_for_implementation,
    create_branch,
    generate_branch_name,
    infer_branch_type,
)

__all__ = [
    "GitWorkflowPlugin",
    "BranchType",
    "BranchResult",
    "GitStatus",
    "get_git_status",
    "get_current_branch",
    "is_git_repo",
    "is_feature_branch",
    "ensure_feature_branch",
    "prepare_for_implementation",
    "create_branch",
    "generate_branch_name",
    "infer_branch_type",
]

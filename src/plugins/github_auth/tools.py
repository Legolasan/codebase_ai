"""Enhanced git and GitHub tools with authentication.

These tools extend the basic git operations with:
- Clone private repositories
- Push/pull with authentication
- GitHub API operations (PRs, issues)
"""

import logging
import subprocess
import os
from pathlib import Path
from typing import Optional

# Try to import langchain tools (may not be installed)
try:
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func):
        return func

from .auth import GitHubAuth

logger = logging.getLogger(__name__)


def _run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 60,
    auth: Optional[GitHubAuth] = None,
) -> tuple[bool, str]:
    """Run a git command with optional authentication.

    Args:
        args: Git command arguments (without 'git')
        cwd: Working directory
        timeout: Command timeout in seconds
        auth: Optional GitHubAuth instance for authenticated operations

    Returns:
        Tuple of (success, output)
    """
    cmd = ["git"] + args

    env = os.environ.copy()

    # Configure authentication for HTTPS
    if auth:
        token = auth.get_token()
        if token:
            # Use credential helper with token
            env["GIT_ASKPASS"] = "echo"
            env["GIT_TERMINAL_PROMPT"] = "0"
            # For HTTPS URLs, we'll use the token in credential helper

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, f"Command failed: {e}"


def _run_gh_command(
    args: list[str],
    timeout: int = 30,
) -> tuple[bool, str]:
    """Run a GitHub CLI command.

    Args:
        args: gh command arguments (without 'gh')
        timeout: Command timeout in seconds

    Returns:
        Tuple of (success, output)
    """
    cmd = ["gh"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, "GitHub CLI (gh) not installed. Install from https://cli.github.com/"
    except Exception as e:
        return False, f"Command failed: {e}"


def create_git_tools(auth: GitHubAuth) -> list:
    """Create git tools with authentication context.

    Args:
        auth: GitHubAuth instance for authenticated operations

    Returns:
        List of LangChain tools
    """

    @tool
    def git_clone(
        repo_url: str,
        target_dir: Optional[str] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> str:
        """Clone a repository (supports private repos with auth).

        Args:
            repo_url: Repository URL (HTTPS or SSH)
            target_dir: Target directory name (optional)
            branch: Specific branch to clone (optional)
            depth: Shallow clone depth (optional)

        Returns:
            Success message or error
        """
        args = ["clone"]

        if branch:
            args.extend(["-b", branch])
        if depth:
            args.extend(["--depth", str(depth)])

        # Convert SSH to HTTPS if we have a token but no SSH
        if repo_url.startswith("git@github.com:") and auth.get_token():
            # Convert git@github.com:user/repo.git to https://github.com/user/repo.git
            path = repo_url.replace("git@github.com:", "").replace(".git", "")
            token = auth.get_token()
            repo_url = f"https://{token}@github.com/{path}.git"

        args.append(repo_url)

        if target_dir:
            args.append(target_dir)

        success, output = _run_git_command(args, auth=auth, timeout=120)

        if success:
            return f"Successfully cloned {repo_url}"
        else:
            return f"Clone failed: {output}"

    @tool
    def git_push(
        remote: str = "origin",
        branch: Optional[str] = None,
        set_upstream: bool = False,
        force: bool = False,
    ) -> str:
        """Push commits to remote repository.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to push (default: current branch)
            set_upstream: Set upstream tracking (-u flag)
            force: Force push (use with caution!)

        Returns:
            Push result message
        """
        args = ["push"]

        if set_upstream:
            args.append("-u")
        if force:
            args.append("--force")

        args.append(remote)

        if branch:
            args.append(branch)

        success, output = _run_git_command(args, auth=auth)

        if success:
            return f"Successfully pushed to {remote}"
        else:
            return f"Push failed: {output}"

    @tool
    def git_pull(
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False,
    ) -> str:
        """Pull changes from remote repository.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to pull (default: current branch)
            rebase: Use rebase instead of merge

        Returns:
            Pull result message
        """
        args = ["pull"]

        if rebase:
            args.append("--rebase")

        args.append(remote)

        if branch:
            args.append(branch)

        success, output = _run_git_command(args, auth=auth)

        if success:
            return f"Successfully pulled from {remote}: {output}"
        else:
            return f"Pull failed: {output}"

    @tool
    def git_fetch(
        remote: str = "origin",
        prune: bool = False,
        all_remotes: bool = False,
    ) -> str:
        """Fetch changes from remote repository.

        Args:
            remote: Remote name (default: origin)
            prune: Remove deleted remote branches
            all_remotes: Fetch from all remotes

        Returns:
            Fetch result message
        """
        args = ["fetch"]

        if prune:
            args.append("--prune")
        if all_remotes:
            args.append("--all")
        else:
            args.append(remote)

        success, output = _run_git_command(args, auth=auth)

        if success:
            return f"Fetch complete: {output}" if output else "Fetch complete"
        else:
            return f"Fetch failed: {output}"

    @tool
    def gh_create_pr(
        title: str,
        body: str,
        base: str = "main",
        draft: bool = False,
        labels: Optional[str] = None,
    ) -> str:
        """Create a GitHub pull request using gh CLI.

        Args:
            title: PR title
            body: PR description
            base: Base branch (default: main)
            draft: Create as draft PR
            labels: Comma-separated labels

        Returns:
            PR URL or error message
        """
        args = ["pr", "create", "--title", title, "--body", body, "--base", base]

        if draft:
            args.append("--draft")
        if labels:
            args.extend(["--label", labels])

        success, output = _run_gh_command(args)

        if success:
            return f"PR created: {output}"
        else:
            return f"Failed to create PR: {output}"

    @tool
    def gh_create_issue(
        title: str,
        body: str,
        labels: Optional[str] = None,
        assignees: Optional[str] = None,
    ) -> str:
        """Create a GitHub issue using gh CLI.

        Args:
            title: Issue title
            body: Issue description
            labels: Comma-separated labels
            assignees: Comma-separated assignees

        Returns:
            Issue URL or error message
        """
        args = ["issue", "create", "--title", title, "--body", body]

        if labels:
            args.extend(["--label", labels])
        if assignees:
            args.extend(["--assignee", assignees])

        success, output = _run_gh_command(args)

        if success:
            return f"Issue created: {output}"
        else:
            return f"Failed to create issue: {output}"

    @tool
    def gh_pr_list(
        state: str = "open",
        limit: int = 10,
    ) -> str:
        """List pull requests using gh CLI.

        Args:
            state: PR state (open, closed, merged, all)
            limit: Maximum number of PRs to list

        Returns:
            List of PRs or error message
        """
        args = ["pr", "list", "--state", state, "--limit", str(limit)]

        success, output = _run_gh_command(args)

        if success:
            return output if output else "No pull requests found"
        else:
            return f"Failed to list PRs: {output}"

    @tool
    def gh_pr_view(
        pr_number: int,
    ) -> str:
        """View a specific pull request.

        Args:
            pr_number: PR number to view

        Returns:
            PR details or error message
        """
        args = ["pr", "view", str(pr_number)]

        success, output = _run_gh_command(args)

        if success:
            return output
        else:
            return f"Failed to view PR #{pr_number}: {output}"

    @tool
    def gh_issue_list(
        state: str = "open",
        limit: int = 10,
        labels: Optional[str] = None,
    ) -> str:
        """List issues using gh CLI.

        Args:
            state: Issue state (open, closed, all)
            limit: Maximum number of issues to list
            labels: Filter by labels (comma-separated)

        Returns:
            List of issues or error message
        """
        args = ["issue", "list", "--state", state, "--limit", str(limit)]

        if labels:
            args.extend(["--label", labels])

        success, output = _run_gh_command(args)

        if success:
            return output if output else "No issues found"
        else:
            return f"Failed to list issues: {output}"

    @tool
    def gh_repo_view() -> str:
        """View current repository information.

        Returns:
            Repository details or error message
        """
        args = ["repo", "view"]

        success, output = _run_gh_command(args)

        if success:
            return output
        else:
            return f"Failed to view repo: {output}"

    return [
        git_clone,
        git_push,
        git_pull,
        git_fetch,
        gh_create_pr,
        gh_create_issue,
        gh_pr_list,
        gh_pr_view,
        gh_issue_list,
        gh_repo_view,
    ]

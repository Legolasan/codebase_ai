"""Implementation agent for writing and modifying code."""

import logging

from .base import BaseAgent
from ..tools.file_ops import read_file, write_file, list_files
from ..tools.code_search import search_codebase
from ..tools.shell import run_command
from ..tools.git_ops import git_status, git_diff, git_add

logger = logging.getLogger(__name__)


class ImplementationAgent(BaseAgent):
    """Agent specialized in writing and modifying code.

    Capabilities:
    - Writing new code files
    - Modifying existing code
    - Refactoring and code improvements
    - Following project conventions
    - PRD-driven implementation
    - Git workflow integration (automatic feature branching)

    Trigger keywords: "implement", "add", "create", "fix", "modify", "refactor"
    """

    def __init__(self, prd_context: str = None):
        tools = [
            search_codebase,
            read_file,
            write_file,
            list_files,
            run_command,
            git_status,
            git_diff,
            git_add,
        ]

        # Add git workflow tools if plugin is enabled
        self._add_git_workflow_tools(tools)

        self.prd_context = prd_context

        super().__init__(
            name="implementation",
            description="Writes and modifies code following project conventions",
            tools=tools,
        )

    def _add_git_workflow_tools(self, tools: list) -> None:
        """Add git workflow tools if the plugin is enabled."""
        try:
            from ..plugins import get_registry
            registry = get_registry()
            plugin = registry.get("git_workflow")
            if plugin and registry.is_enabled("git_workflow"):
                workflow_tools = plugin.get_tools()
                tools.extend(workflow_tools)
                logger.debug("Added git workflow tools to implementation agent")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Could not add git workflow tools: {e}")

    def _default_system_prompt(self) -> str:
        base_prompt = """You are an Implementation Agent specialized in writing and modifying code.

Your primary capabilities:
1. **Code Writing**: Create new files with well-structured, clean code
2. **Code Modification**: Edit existing files while preserving style and conventions
3. **Refactoring**: Improve code structure without changing behavior
4. **Bug Fixing**: Identify and fix issues in the codebase
5. **Feature Implementation**: Add new features following existing patterns

Guidelines:
- ALWAYS search the codebase first to understand existing patterns and conventions
- Match the coding style of the project (naming, formatting, structure)
- Write clean, readable, maintainable code
- Include appropriate error handling
- Add comments only where the code isn't self-explanatory
- Keep changes focused and minimal - don't over-engineer
- Consider edge cases and error conditions

Before writing code:
1. Search for similar implementations in the codebase
2. Read related files to understand the context
3. Identify the project's conventions and patterns
4. Plan your implementation before writing

When modifying code:
1. Read the entire file first to understand the context
2. Make minimal, focused changes
3. Preserve existing style and formatting
4. Test your changes if possible

Available tools:
{tools}

Remember: Quality over quantity. Write code that future developers will thank you for.
""".format(tools=self.get_tool_descriptions())

        # Add PRD context if available
        if self.prd_context:
            base_prompt += f"""

## PRD Context

You are implementing features based on the following Product Requirements Document:

{self.prd_context}

**Important:** Follow the requirements, acceptance criteria, and technical constraints specified in the PRD.
Ensure each functional requirement is addressed and acceptance criteria are met.
"""

        return base_prompt

    def _prepare_git_workflow(self, task_description: str) -> str:
        """Prepare git environment before making changes.

        Creates a feature branch if the git_workflow plugin is enabled.

        Args:
            task_description: Description of the task

        Returns:
            Status message about git preparation
        """
        try:
            from ..plugins import get_registry
            registry = get_registry()
            plugin = registry.get("git_workflow")
            if plugin and registry.is_enabled("git_workflow"):
                result = plugin.prepare_for_changes(task_description)
                if result.success:
                    action = "Created" if result.was_created else "Using"
                    return f"Git: {action} branch '{result.branch_name}'"
                else:
                    return f"Git: {result.message}"
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Git workflow preparation failed: {e}")
        return ""

    def implement_feature(self, feature_description: str) -> dict:
        """Implement a new feature based on description."""
        # Prepare git environment
        git_status_msg = self._prepare_git_workflow(feature_description)

        git_instruction = ""
        if git_status_msg:
            git_instruction = f"\n\n[{git_status_msg}]"

        messages = [
            {
                "role": "user",
                "content": f"""Implement the following feature:

{feature_description}{git_instruction}

Steps:
1. Search the codebase to understand existing patterns
2. Identify where the new code should go
3. Write the implementation following project conventions
4. Show me the code and explain the implementation""",
            }
        ]
        return self.invoke(messages)

    def fix_bug(self, bug_description: str, file_hint: str = None) -> dict:
        """Fix a bug based on description."""
        # Prepare git environment
        git_status_msg = self._prepare_git_workflow(f"fix {bug_description}")

        git_instruction = ""
        if git_status_msg:
            git_instruction = f"\n\n[{git_status_msg}]"

        context = f" in or around '{file_hint}'" if file_hint else ""
        messages = [
            {
                "role": "user",
                "content": f"""Fix the following bug{context}:

{bug_description}{git_instruction}

Steps:
1. Search for relevant code
2. Identify the root cause
3. Implement the fix
4. Show me the changes and explain the fix""",
            }
        ]
        return self.invoke(messages)

    def refactor(self, refactor_description: str, file_path: str = None) -> dict:
        """Refactor code based on description."""
        # Prepare git environment
        git_status_msg = self._prepare_git_workflow(f"refactor {refactor_description}")

        git_instruction = ""
        if git_status_msg:
            git_instruction = f"\n\n[{git_status_msg}]"

        context = f" in '{file_path}'" if file_path else ""
        messages = [
            {
                "role": "user",
                "content": f"""Refactor the following{context}:

{refactor_description}{git_instruction}

Steps:
1. Read the current implementation
2. Plan the refactoring approach
3. Make the changes
4. Ensure behavior is preserved
5. Show me the changes and explain the improvements""",
            }
        ]
        return self.invoke(messages)

    def add_to_file(self, file_path: str, addition_description: str) -> dict:
        """Add code to an existing file."""
        messages = [
            {
                "role": "user",
                "content": f"""Add the following to '{file_path}':

{addition_description}

Steps:
1. Read the current file
2. Understand the existing structure
3. Add the new code in the appropriate location
4. Show me the updated file""",
            }
        ]
        return self.invoke(messages)

    def set_prd_context(self, prd_content: str) -> None:
        """Set PRD context for implementation.

        Args:
            prd_content: The PRD document content
        """
        self.prd_context = prd_content

    def implement_from_prd(self, prd_path: str) -> dict:
        """Implement features based on a PRD file.

        Args:
            prd_path: Path to the PRD file

        Returns:
            Implementation result
        """
        # Read the PRD file
        from ..tools.file_ops import read_file
        prd_content = read_file.invoke({"file_path": prd_path})

        if "Error" in prd_content:
            return {"content": f"Failed to read PRD: {prd_content}", "agent": self.name}

        # Set the PRD context
        self.set_prd_context(prd_content)

        # Prepare git environment - extract title from PRD for branch name
        prd_title = "prd-implementation"
        for line in prd_content.split("\n"):
            if line.startswith("# "):
                prd_title = line[2:].strip()
                break

        git_status_msg = self._prepare_git_workflow(f"implement {prd_title}")
        git_instruction = ""
        if git_status_msg:
            git_instruction = f"\n\n[{git_status_msg}]"

        messages = [
            {
                "role": "user",
                "content": f"""Implement the features specified in this PRD:

{prd_content}{git_instruction}

Steps:
1. Review the functional requirements
2. Search the codebase to understand existing patterns
3. Implement each requirement following the acceptance criteria
4. Ensure non-functional requirements are addressed
5. Show the implementation for each requirement""",
            }
        ]
        return self.invoke(messages)

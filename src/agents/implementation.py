"""Implementation agent for writing and modifying code."""

from .base import BaseAgent
from ..tools.file_ops import read_file, write_file, list_files
from ..tools.code_search import search_codebase
from ..tools.shell import run_command
from ..tools.git_ops import git_status, git_diff, git_add


class ImplementationAgent(BaseAgent):
    """Agent specialized in writing and modifying code.

    Capabilities:
    - Writing new code files
    - Modifying existing code
    - Refactoring and code improvements
    - Following project conventions

    Trigger keywords: "implement", "add", "create", "fix", "modify", "refactor"
    """

    def __init__(self):
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

        super().__init__(
            name="implementation",
            description="Writes and modifies code following project conventions",
            tools=tools,
        )

    def _default_system_prompt(self) -> str:
        return """You are an Implementation Agent specialized in writing and modifying code.

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

    def implement_feature(self, feature_description: str) -> dict:
        """Implement a new feature based on description."""
        messages = [
            {
                "role": "user",
                "content": f"""Implement the following feature:

{feature_description}

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
        context = f" in or around '{file_hint}'" if file_hint else ""
        messages = [
            {
                "role": "user",
                "content": f"""Fix the following bug{context}:

{bug_description}

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
        context = f" in '{file_path}'" if file_path else ""
        messages = [
            {
                "role": "user",
                "content": f"""Refactor the following{context}:

{refactor_description}

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

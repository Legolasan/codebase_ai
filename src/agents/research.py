"""Research agent for code exploration and analysis."""

from .base import BaseAgent
from ..tools.file_ops import read_file, list_files, file_info
from ..tools.code_search import search_codebase, find_similar_code, get_file_chunks
from ..tools.git_ops import git_log, git_blame, git_show


class ResearchAgent(BaseAgent):
    """Agent specialized in exploring and understanding codebases.

    Capabilities:
    - Semantic code search using RAG
    - File exploration and reading
    - Pattern identification
    - Code path tracing
    - Git history analysis

    Trigger keywords: "find", "where", "how does", "explain", "what is"
    """

    def __init__(self):
        tools = [
            search_codebase,
            find_similar_code,
            get_file_chunks,
            read_file,
            list_files,
            file_info,
            git_log,
            git_blame,
            git_show,
        ]

        super().__init__(
            name="research",
            description="Explores and analyzes codebases to find information and understand patterns",
            tools=tools,
        )

    def _default_system_prompt(self) -> str:
        return """You are a Research Agent specialized in exploring and understanding codebases.

Your primary capabilities:
1. **Semantic Code Search**: Use search_codebase to find relevant code using natural language queries
2. **File Exploration**: Read files, list directories, and understand project structure
3. **Pattern Analysis**: Identify coding patterns, conventions, and architectural decisions
4. **Code Tracing**: Follow code paths, understand call chains, and map dependencies
5. **Git History**: Analyze commit history to understand code evolution

Guidelines:
- Start with semantic search to find relevant areas, then drill down into specific files
- When explaining code, provide context about where it fits in the larger system
- Look for patterns and conventions used throughout the codebase
- Use git history to understand why code was written a certain way
- Be thorough but concise in your explanations
- Reference specific files and line numbers when discussing code

Available tools:
{tools}

When answering questions:
1. First search for relevant code using semantic search
2. Read the most relevant files to understand the implementation
3. Trace through the code to understand the full picture
4. Provide clear, structured explanations with code references
""".format(tools=self.get_tool_descriptions())

    def search(self, query: str, n_results: int = 5) -> str:
        """Quick helper to search the codebase."""
        return self.run_tool("search_codebase", {"query": query, "n_results": n_results})

    def explain_file(self, file_path: str) -> dict:
        """Analyze and explain a file's purpose and structure."""
        messages = [
            {
                "role": "user",
                "content": f"Read and analyze the file '{file_path}'. Explain its purpose, key components, and how it fits into the codebase.",
            }
        ]
        return self.invoke(messages)

    def trace_code_path(self, start_point: str) -> dict:
        """Trace a code path from a starting point (function, class, etc.)."""
        messages = [
            {
                "role": "user",
                "content": f"Trace the code path starting from '{start_point}'. Find where it's defined, how it's used, and what it depends on.",
            }
        ]
        return self.invoke(messages)

    def find_pattern(self, pattern_description: str) -> dict:
        """Find examples of a pattern in the codebase."""
        messages = [
            {
                "role": "user",
                "content": f"Search the codebase for examples of: {pattern_description}. Show relevant code snippets and explain the pattern.",
            }
        ]
        return self.invoke(messages)

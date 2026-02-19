"""Review agent for code review and quality suggestions."""

from .base import BaseAgent
from ..tools.file_ops import read_file, list_files, file_info
from ..tools.code_search import search_codebase, find_similar_code
from ..tools.git_ops import git_diff, git_log, git_blame


class ReviewAgent(BaseAgent):
    """Agent specialized in code review and quality analysis.

    Capabilities:
    - Code review and feedback
    - Quality assessment
    - Security analysis
    - Performance suggestions
    - Best practice recommendations

    Trigger keywords: "review", "check", "improve", "quality", "security"
    """

    def __init__(self):
        tools = [
            search_codebase,
            find_similar_code,
            read_file,
            list_files,
            file_info,
            git_diff,
            git_log,
            git_blame,
        ]

        super().__init__(
            name="review",
            description="Reviews code for quality, security, and best practices",
            tools=tools,
        )

    def _default_system_prompt(self) -> str:
        return """You are a Review Agent specialized in code review and quality analysis.

Your primary capabilities:
1. **Code Review**: Provide constructive feedback on code changes
2. **Quality Assessment**: Evaluate code quality, readability, and maintainability
3. **Security Analysis**: Identify potential security vulnerabilities
4. **Performance Review**: Spot performance issues and optimization opportunities
5. **Best Practices**: Ensure code follows best practices and conventions

Review categories:
- **Correctness**: Does the code do what it's supposed to do?
- **Security**: Are there any security vulnerabilities?
- **Performance**: Are there any performance concerns?
- **Maintainability**: Is the code easy to understand and modify?
- **Style**: Does it follow project conventions?
- **Testing**: Is the code adequately tested?

Guidelines:
- Be constructive and specific - explain why something is an issue
- Prioritize issues by severity (critical, major, minor, suggestion)
- Provide concrete suggestions for improvement
- Acknowledge good patterns and practices
- Consider the context and constraints
- Look for similar code in the codebase for consistency

Review format:
For each issue:
1. Location (file:line)
2. Severity (critical/major/minor/suggestion)
3. Category (correctness/security/performance/maintainability/style)
4. Description of the issue
5. Suggested fix

Available tools:
{tools}

Remember: The goal is to help improve the code, not to criticize the author.
""".format(tools=self.get_tool_descriptions())

    def review_file(self, file_path: str) -> dict:
        """Review a specific file."""
        messages = [
            {
                "role": "user",
                "content": f"""Review the file '{file_path}':

1. Read the file
2. Analyze for issues across all categories
3. Look for similar code in the codebase for context
4. Provide structured feedback
5. Summarize with overall assessment""",
            }
        ]
        return self.invoke(messages)

    def review_changes(self, branch: str = None) -> dict:
        """Review uncommitted changes or changes in a branch."""
        context = f" in branch '{branch}'" if branch else ""
        messages = [
            {
                "role": "user",
                "content": f"""Review the code changes{context}:

1. Get the diff of changes
2. Analyze each changed file
3. Check for issues introduced by the changes
4. Consider impact on existing code
5. Provide structured review feedback""",
            }
        ]
        return self.invoke(messages)

    def security_audit(self, target: str = None) -> dict:
        """Perform a security-focused review."""
        context = f" of '{target}'" if target else ""
        messages = [
            {
                "role": "user",
                "content": f"""Perform a security audit{context}:

Look for:
- Input validation issues
- Authentication/authorization problems
- SQL injection vulnerabilities
- XSS vulnerabilities
- Sensitive data exposure
- Insecure dependencies
- Hardcoded secrets
- OWASP Top 10 issues

For each issue found:
1. Describe the vulnerability
2. Explain the risk
3. Provide remediation steps""",
            }
        ]
        return self.invoke(messages)

    def performance_review(self, target: str) -> dict:
        """Review code for performance issues."""
        messages = [
            {
                "role": "user",
                "content": f"""Review '{target}' for performance issues:

Look for:
- Inefficient algorithms (O(n²) where O(n) is possible)
- Unnecessary database queries (N+1 problems)
- Memory leaks
- Blocking operations
- Unnecessary computations
- Missing caching opportunities
- Large data structures in memory

For each issue:
1. Describe the problem
2. Estimate the impact
3. Suggest optimization""",
            }
        ]
        return self.invoke(messages)

    def suggest_improvements(self, file_path: str) -> dict:
        """Suggest improvements for a file (without reporting issues)."""
        messages = [
            {
                "role": "user",
                "content": f"""Suggest improvements for '{file_path}':

Focus on:
- Code organization and structure
- Readability enhancements
- Useful abstractions
- Documentation improvements
- Testing suggestions

Be constructive and explain the benefits of each suggestion.""",
            }
        ]
        return self.invoke(messages)

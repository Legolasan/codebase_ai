"""Testing agent for test generation and execution."""

from .base import BaseAgent
from ..tools.file_ops import read_file, write_file, list_files
from ..tools.code_search import search_codebase
from ..tools.shell import run_command, run_tests


class TestingAgent(BaseAgent):
    """Agent specialized in testing and quality assurance.

    Capabilities:
    - Generating unit tests
    - Generating integration tests
    - Running test suites
    - Analyzing test coverage
    - Identifying test gaps

    Trigger keywords: "test", "verify", "coverage", "unit test", "integration test"
    """

    def __init__(self):
        tools = [
            search_codebase,
            read_file,
            write_file,
            list_files,
            run_command,
            run_tests,
        ]

        super().__init__(
            name="testing",
            description="Generates and runs tests to ensure code quality",
            tools=tools,
        )

    def _default_system_prompt(self) -> str:
        return """You are a Testing Agent specialized in test generation and quality assurance.

Your primary capabilities:
1. **Unit Test Generation**: Create focused tests for individual functions/methods
2. **Integration Test Generation**: Create tests for component interactions
3. **Test Execution**: Run test suites and analyze results
4. **Coverage Analysis**: Identify untested code paths
5. **Test Improvement**: Suggest improvements to existing tests

Testing principles:
- Tests should be independent and repeatable
- Test one thing at a time (single responsibility)
- Use descriptive test names that explain what's being tested
- Include edge cases and error conditions
- Arrange-Act-Assert pattern for unit tests
- Mock external dependencies appropriately

When generating tests:
1. First read the code to be tested
2. Identify the key behaviors to test
3. Consider edge cases, error conditions, and boundary values
4. Match the project's testing framework and conventions
5. Write clear, maintainable tests

Test naming conventions:
- test_<function>_<scenario>_<expected_result>
- Or: test_<behavior_being_tested>

Available tools:
{tools}

Remember: Good tests are documentation. They should clearly show how the code is meant to be used.
""".format(tools=self.get_tool_descriptions())

    def generate_tests(self, target: str, test_type: str = "unit") -> dict:
        """Generate tests for a specific target (file, function, class)."""
        messages = [
            {
                "role": "user",
                "content": f"""Generate {test_type} tests for: {target}

Steps:
1. Read the target code
2. Identify key behaviors and edge cases
3. Search for existing test patterns in the project
4. Generate comprehensive tests
5. Write the tests to an appropriate file
6. Show me the generated tests""",
            }
        ]
        return self.invoke(messages)

    def run_and_report(self, test_path: str = None) -> dict:
        """Run tests and generate a report."""
        context = f" for '{test_path}'" if test_path else ""
        messages = [
            {
                "role": "user",
                "content": f"""Run the tests{context} and provide a report:

1. Run the test suite
2. Analyze the results
3. Identify any failures
4. Suggest fixes for failing tests
5. Provide a summary report""",
            }
        ]
        return self.invoke(messages)

    def analyze_coverage(self, target: str = None) -> dict:
        """Analyze test coverage for a target."""
        context = f" for '{target}'" if target else ""
        messages = [
            {
                "role": "user",
                "content": f"""Analyze test coverage{context}:

1. Run coverage analysis
2. Identify untested code paths
3. Prioritize what needs testing
4. Suggest specific tests to add
5. Provide a coverage report""",
            }
        ]
        return self.invoke(messages)

    def suggest_test_cases(self, target: str) -> dict:
        """Suggest test cases for a target without generating full tests."""
        messages = [
            {
                "role": "user",
                "content": f"""Suggest test cases for: {target}

1. Read the target code
2. Identify all code paths and behaviors
3. List test cases that should exist
4. Include edge cases and error conditions
5. Prioritize by importance""",
            }
        ]
        return self.invoke(messages)

    def fix_failing_test(self, test_output: str) -> dict:
        """Analyze and fix a failing test."""
        messages = [
            {
                "role": "user",
                "content": f"""A test is failing. Analyze and fix it:

Test output:
{test_output}

Steps:
1. Understand what the test is checking
2. Identify why it's failing
3. Determine if it's a test bug or code bug
4. Fix the issue
5. Verify the fix""",
            }
        ]
        return self.invoke(messages)

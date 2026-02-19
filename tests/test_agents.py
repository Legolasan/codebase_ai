"""Tests for the agents module."""

import pytest
from unittest.mock import MagicMock, patch


class TestOrchestratorAgent:
    """Tests for task routing in OrchestratorAgent."""

    def test_classify_research_keywords(self):
        """Test classification of research-related requests."""
        from src.agents.orchestrator import OrchestratorAgent

        with patch.object(OrchestratorAgent, '__init__', lambda x: None):
            orchestrator = OrchestratorAgent()
            orchestrator.agents = {"research": None, "implementation": None, "testing": None, "review": None}

            # Mock LLM to avoid API calls
            orchestrator.llm = MagicMock()

            test_cases = [
                ("Where is the login function?", "research"),
                ("How does authentication work?", "research"),
                ("Find all API endpoints", "research"),
                ("Explain the database schema", "research"),
            ]

            for request, expected in test_cases:
                result = orchestrator._classify_task(request)
                assert result == expected, f"Expected '{expected}' for '{request}', got '{result}'"

    def test_classify_implementation_keywords(self):
        """Test classification of implementation-related requests."""
        from src.agents.orchestrator import OrchestratorAgent

        with patch.object(OrchestratorAgent, '__init__', lambda x: None):
            orchestrator = OrchestratorAgent()
            orchestrator.agents = {"research": None, "implementation": None, "testing": None, "review": None}
            orchestrator.llm = MagicMock()

            test_cases = [
                ("Implement a login feature", "implementation"),
                ("Add validation to the form", "implementation"),
                ("Fix the authentication bug", "implementation"),
                ("Create a new API endpoint", "implementation"),
            ]

            for request, expected in test_cases:
                result = orchestrator._classify_task(request)
                assert result == expected, f"Expected '{expected}' for '{request}', got '{result}'"

    def test_classify_testing_keywords(self):
        """Test classification of testing-related requests."""
        from src.agents.orchestrator import OrchestratorAgent

        with patch.object(OrchestratorAgent, '__init__', lambda x: None):
            orchestrator = OrchestratorAgent()
            orchestrator.agents = {"research": None, "implementation": None, "testing": None, "review": None}
            orchestrator.llm = MagicMock()

            test_cases = [
                ("Write tests for the login", "testing"),
                ("Test the API endpoints", "testing"),
                ("Check test coverage", "testing"),
                ("Unit test the user service", "testing"),
            ]

            for request, expected in test_cases:
                result = orchestrator._classify_task(request)
                assert result == expected, f"Expected '{expected}' for '{request}', got '{result}'"

    def test_classify_review_keywords(self):
        """Test classification of review-related requests."""
        from src.agents.orchestrator import OrchestratorAgent

        with patch.object(OrchestratorAgent, '__init__', lambda x: None):
            orchestrator = OrchestratorAgent()
            orchestrator.agents = {"research": None, "implementation": None, "testing": None, "review": None}
            orchestrator.llm = MagicMock()

            test_cases = [
                ("Review the authentication code", "review"),
                ("Check for security issues", "review"),
                ("Improve code quality", "review"),
                ("Audit the API handlers", "review"),
            ]

            for request, expected in test_cases:
                result = orchestrator._classify_task(request)
                assert result == expected, f"Expected '{expected}' for '{request}', got '{result}'"


class TestBaseAgent:
    """Tests for BaseAgent functionality."""

    def test_get_tool_descriptions(self):
        """Test tool description generation."""
        from src.agents.base import BaseAgent
        from langchain_core.tools import tool

        @tool
        def test_tool(x: str) -> str:
            """A test tool for testing."""
            return x

        class TestAgent(BaseAgent):
            def _default_system_prompt(self) -> str:
                return "Test prompt"

        with patch('src.agents.base.ChatAnthropic'):
            agent = TestAgent(
                name="test",
                description="Test agent",
                tools=[test_tool],
            )

            descriptions = agent.get_tool_descriptions()
            assert "test_tool" in descriptions
            assert "test tool for testing" in descriptions

    def test_run_tool(self):
        """Test tool execution by name."""
        from src.agents.base import BaseAgent
        from langchain_core.tools import tool

        @tool
        def echo_tool(message: str) -> str:
            """Echo the message back."""
            return f"Echo: {message}"

        class TestAgent(BaseAgent):
            def _default_system_prompt(self) -> str:
                return "Test prompt"

        with patch('src.agents.base.ChatAnthropic'):
            agent = TestAgent(
                name="test",
                description="Test agent",
                tools=[echo_tool],
            )

            result = agent.run_tool("echo_tool", {"message": "hello"})
            assert result == "Echo: hello"

    def test_run_unknown_tool(self):
        """Test error handling for unknown tools."""
        from src.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def _default_system_prompt(self) -> str:
                return "Test prompt"

        with patch('src.agents.base.ChatAnthropic'):
            agent = TestAgent(
                name="test",
                description="Test agent",
                tools=[],
            )

            result = agent.run_tool("nonexistent", {})
            assert "not found" in result.lower()

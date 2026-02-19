"""Shared state definition for LangGraph workflow."""

from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import add_messages


class TaskType(str, Enum):
    """Types of tasks the system can handle."""

    RESEARCH = "research"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    MULTI_AGENT = "multi_agent"


class AgentState(TypedDict):
    """Shared state for the agent workflow.

    This state is passed between all nodes in the LangGraph workflow.
    """

    # User request
    request: str

    # Conversation messages (accumulates with add_messages)
    messages: Annotated[list, add_messages]

    # Routing information
    task_type: Optional[TaskType]
    current_agent: Optional[str]

    # Agent results
    research_result: Optional[str]
    implementation_result: Optional[str]
    testing_result: Optional[str]
    review_result: Optional[str]

    # Final aggregated result
    final_result: Optional[str]

    # Workflow control
    next_step: Optional[str]
    needs_review: bool
    needs_testing: bool
    iteration_count: int
    max_iterations: int

    # Context from RAG
    code_context: list[dict]

    # Error tracking
    error: Optional[str]


def create_initial_state(
    request: str,
    max_iterations: int = 5,
) -> AgentState:
    """Create an initial state for a new workflow.

    Args:
        request: The user's initial request
        max_iterations: Maximum number of agent iterations

    Returns:
        Initialized AgentState
    """
    return AgentState(
        request=request,
        messages=[],
        task_type=None,
        current_agent=None,
        research_result=None,
        implementation_result=None,
        testing_result=None,
        review_result=None,
        final_result=None,
        next_step=None,
        needs_review=False,
        needs_testing=False,
        iteration_count=0,
        max_iterations=max_iterations,
        code_context=[],
        error=None,
    )

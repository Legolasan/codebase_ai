"""LangGraph workflow for agent orchestration."""

from typing import Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from .state import AgentState, TaskType, create_initial_state
from ..agents import (
    OrchestratorAgent,
    ResearchAgent,
    ImplementationAgent,
    TestingAgent,
    ReviewAgent,
)
from ..tools.code_search import get_vector_store


# Initialize agents
orchestrator = OrchestratorAgent()
research_agent = ResearchAgent()
implementation_agent = ImplementationAgent()
testing_agent = TestingAgent()
review_agent = ReviewAgent()


def router_node(state: AgentState) -> AgentState:
    """Route the request to the appropriate agent."""
    request = state["request"]

    # Classify the task
    agent_name, _ = orchestrator.route(request)

    # Map to TaskType
    task_type_map = {
        "research": TaskType.RESEARCH,
        "implementation": TaskType.IMPLEMENTATION,
        "testing": TaskType.TESTING,
        "review": TaskType.REVIEW,
    }

    state["task_type"] = task_type_map.get(agent_name, TaskType.RESEARCH)
    state["current_agent"] = agent_name
    state["next_step"] = agent_name

    # Add routing message
    state["messages"] = [
        HumanMessage(content=request),
        AIMessage(content=f"Routing to {agent_name} agent..."),
    ]

    return state


def fetch_context_node(state: AgentState) -> AgentState:
    """Fetch relevant code context using RAG."""
    request = state["request"]
    vector_store = get_vector_store()

    if vector_store:
        try:
            results = vector_store.search(request, n_results=3)
            state["code_context"] = results
        except Exception as e:
            state["code_context"] = []
            state["error"] = f"Context fetch error: {str(e)}"
    else:
        state["code_context"] = []

    return state


def research_node(state: AgentState) -> AgentState:
    """Execute the research agent."""
    messages = _build_messages(state)

    try:
        result = research_agent.invoke(messages)
        state["research_result"] = result.get("content", "")
        state["messages"] = state["messages"] + [
            AIMessage(content=f"[Research Agent]\n{result.get('content', '')}")
        ]

        # Check if implementation is needed
        if _needs_implementation(result.get("content", ""), state["request"]):
            state["next_step"] = "implementation"
        else:
            state["next_step"] = "complete"

    except Exception as e:
        state["error"] = f"Research error: {str(e)}"
        state["next_step"] = "complete"

    state["iteration_count"] += 1
    return state


def implementation_node(state: AgentState) -> AgentState:
    """Execute the implementation agent."""
    messages = _build_messages(state)

    # Add research context if available
    if state.get("research_result"):
        messages.insert(
            0,
            {"role": "user", "content": f"Research context:\n{state['research_result'][:1000]}"},
        )

    try:
        result = implementation_agent.invoke(messages)
        state["implementation_result"] = result.get("content", "")
        state["messages"] = state["messages"] + [
            AIMessage(content=f"[Implementation Agent]\n{result.get('content', '')}")
        ]

        # Check if testing or review is needed
        if state.get("needs_testing") and state["iteration_count"] < state["max_iterations"]:
            state["next_step"] = "testing"
        elif state.get("needs_review") and state["iteration_count"] < state["max_iterations"]:
            state["next_step"] = "review"
        else:
            state["next_step"] = "complete"

    except Exception as e:
        state["error"] = f"Implementation error: {str(e)}"
        state["next_step"] = "complete"

    state["iteration_count"] += 1
    return state


def testing_node(state: AgentState) -> AgentState:
    """Execute the testing agent."""
    messages = _build_messages(state)

    # Add implementation context
    if state.get("implementation_result"):
        messages.insert(
            0,
            {"role": "user", "content": f"Implementation context:\n{state['implementation_result'][:1000]}"},
        )

    try:
        result = testing_agent.invoke(messages)
        state["testing_result"] = result.get("content", "")
        state["messages"] = state["messages"] + [
            AIMessage(content=f"[Testing Agent]\n{result.get('content', '')}")
        ]

        # Check if review is needed
        if state.get("needs_review") and state["iteration_count"] < state["max_iterations"]:
            state["next_step"] = "review"
        else:
            state["next_step"] = "complete"

    except Exception as e:
        state["error"] = f"Testing error: {str(e)}"
        state["next_step"] = "complete"

    state["iteration_count"] += 1
    return state


def review_node(state: AgentState) -> AgentState:
    """Execute the review agent."""
    messages = _build_messages(state)

    # Add previous context
    context_parts = []
    if state.get("implementation_result"):
        context_parts.append(f"Implementation:\n{state['implementation_result'][:500]}")
    if state.get("testing_result"):
        context_parts.append(f"Testing:\n{state['testing_result'][:500]}")

    if context_parts:
        messages.insert(0, {"role": "user", "content": "\n\n".join(context_parts)})

    try:
        result = review_agent.invoke(messages)
        state["review_result"] = result.get("content", "")
        state["messages"] = state["messages"] + [
            AIMessage(content=f"[Review Agent]\n{result.get('content', '')}")
        ]
        state["next_step"] = "complete"

    except Exception as e:
        state["error"] = f"Review error: {str(e)}"
        state["next_step"] = "complete"

    state["iteration_count"] += 1
    return state


def completion_node(state: AgentState) -> AgentState:
    """Aggregate results and prepare final output."""
    results = []

    if state.get("research_result"):
        results.append(("Research", state["research_result"]))
    if state.get("implementation_result"):
        results.append(("Implementation", state["implementation_result"]))
    if state.get("testing_result"):
        results.append(("Testing", state["testing_result"]))
    if state.get("review_result"):
        results.append(("Review", state["review_result"]))

    if results:
        # Use the most relevant result as the final result
        # For single-agent tasks, this is straightforward
        # For multi-agent, we combine them
        if len(results) == 1:
            state["final_result"] = results[0][1]
        else:
            combined = "\n\n---\n\n".join(
                f"## {name}\n{content}" for name, content in results
            )
            state["final_result"] = combined
    else:
        state["final_result"] = state.get("error", "No results generated.")

    return state


def route_next(state: AgentState) -> Literal["research", "implementation", "testing", "review", "complete"]:
    """Determine the next node based on state."""
    # Check iteration limit
    if state["iteration_count"] >= state["max_iterations"]:
        return "complete"

    # Check for errors
    if state.get("error"):
        return "complete"

    next_step = state.get("next_step", "complete")

    if next_step in ["research", "implementation", "testing", "review"]:
        return next_step

    return "complete"


def _build_messages(state: AgentState) -> list[dict]:
    """Build message list for agent invocation."""
    messages = [{"role": "user", "content": state["request"]}]

    # Add code context if available
    if state.get("code_context"):
        context_str = "\n\nRelevant code from the codebase:\n"
        for ctx in state["code_context"][:3]:
            context_str += f"\n--- {ctx['metadata'].get('file_path', 'unknown')} ---\n"
            context_str += ctx.get("content", "")[:500] + "\n"
        messages[0]["content"] = state["request"] + context_str

    return messages


def _needs_implementation(research_result: str, request: str) -> bool:
    """Check if the research result suggests implementation is needed."""
    implementation_triggers = ["implement", "create", "add", "fix", "modify", "build"]
    request_lower = request.lower()
    return any(trigger in request_lower for trigger in implementation_triggers)


def create_workflow() -> StateGraph:
    """Create the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("fetch_context", fetch_context_node)
    workflow.add_node("research", research_node)
    workflow.add_node("implementation", implementation_node)
    workflow.add_node("testing", testing_node)
    workflow.add_node("review", review_node)
    workflow.add_node("complete", completion_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Add edges
    workflow.add_edge("router", "fetch_context")

    # Conditional routing after fetch_context based on task type
    def route_after_context(state: AgentState) -> str:
        task_type = state.get("task_type")
        if task_type == TaskType.RESEARCH:
            return "research"
        elif task_type == TaskType.IMPLEMENTATION:
            return "implementation"
        elif task_type == TaskType.TESTING:
            return "testing"
        elif task_type == TaskType.REVIEW:
            return "review"
        return "research"  # default

    workflow.add_conditional_edges(
        "fetch_context",
        route_after_context,
        {
            "research": "research",
            "implementation": "implementation",
            "testing": "testing",
            "review": "review",
        },
    )

    # Add conditional edges for each agent node
    workflow.add_conditional_edges("research", route_next)
    workflow.add_conditional_edges("implementation", route_next)
    workflow.add_conditional_edges("testing", route_next)
    workflow.add_conditional_edges("review", route_next)

    # Complete is the end
    workflow.add_edge("complete", END)

    return workflow


def run_workflow(
    request: str,
    needs_testing: bool = False,
    needs_review: bool = False,
    max_iterations: int = 5,
) -> dict:
    """Run the workflow for a given request.

    Args:
        request: The user's request
        needs_testing: Whether to include testing agent
        needs_review: Whether to include review agent
        max_iterations: Maximum number of agent iterations

    Returns:
        Final state with results
    """
    # Create initial state
    state = create_initial_state(request, max_iterations)
    state["needs_testing"] = needs_testing
    state["needs_review"] = needs_review

    # Create and compile workflow
    workflow = create_workflow()
    app = workflow.compile()

    # Run workflow
    final_state = app.invoke(state)

    return final_state

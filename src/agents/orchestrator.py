"""Orchestrator agent that routes tasks to specialized agents."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_config
from ..providers import create_llm
from .base import BaseAgent
from .research import ResearchAgent
from .implementation import ImplementationAgent
from .testing import TestingAgent
from .review import ReviewAgent


# Task routing keywords
TASK_KEYWORDS = {
    "research": [
        "find", "where", "how does", "explain", "what is", "show me",
        "locate", "search", "understand", "analyze", "describe",
    ],
    "implementation": [
        "implement", "add", "create", "fix", "modify", "refactor",
        "write", "build", "develop", "change", "update", "edit",
    ],
    "testing": [
        "test", "verify", "coverage", "unit test", "integration",
        "assert", "mock", "spec", "validate",
    ],
    "review": [
        "review", "check", "improve", "quality", "security",
        "audit", "assess", "evaluate", "inspect",
    ],
}


class OrchestratorAgent:
    """Main orchestrator that analyzes requests and routes to specialized agents.

    The orchestrator:
    1. Analyzes the user's request
    2. Determines which specialized agent(s) should handle it
    3. Routes the request and manages agent handoffs
    4. Aggregates results from multiple agents if needed
    """

    def __init__(self):
        # Create LLM using the factory (supports Anthropic, OpenAI, Ollama)
        self.llm = create_llm()

        # Initialize specialized agents
        self.agents = {
            "research": ResearchAgent(),
            "implementation": ImplementationAgent(),
            "testing": TestingAgent(),
            "review": ReviewAgent(),
        }

    def _classify_task(self, request: str) -> str:
        """Classify the task based on keywords and LLM analysis."""
        request_lower = request.lower()

        # Quick keyword-based classification
        scores = {agent: 0 for agent in TASK_KEYWORDS}

        for agent, keywords in TASK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in request_lower:
                    scores[agent] += 1

        # If clear winner from keywords, use it
        max_score = max(scores.values())
        if max_score > 0:
            winners = [agent for agent, score in scores.items() if score == max_score]
            if len(winners) == 1:
                return winners[0]

        # Use LLM for ambiguous cases
        return self._llm_classify(request)

    def _llm_classify(self, request: str) -> str:
        """Use LLM to classify the task."""
        messages = [
            SystemMessage(content="""Classify the following request into exactly one category:
- research: Finding information, understanding code, exploring the codebase
- implementation: Writing or modifying code, fixing bugs, adding features
- testing: Creating tests, running tests, analyzing coverage
- review: Code review, quality checks, security audits

Respond with ONLY the category name, nothing else."""),
            HumanMessage(content=request),
        ]

        response = self.llm.invoke(messages)
        category = response.content.strip().lower()

        # Validate and default to research if invalid
        if category not in self.agents:
            return "research"

        return category

    def route(self, request: str) -> tuple[str, BaseAgent]:
        """Route a request to the appropriate agent.

        Args:
            request: The user's request

        Returns:
            Tuple of (agent_name, agent_instance)
        """
        agent_name = self._classify_task(request)
        return agent_name, self.agents[agent_name]

    def invoke(self, request: str, conversation_history: list[dict] = None) -> dict:
        """Process a request by routing to the appropriate agent.

        Args:
            request: The user's request
            conversation_history: Optional previous conversation messages

        Returns:
            Response dict with content and metadata
        """
        # Route to appropriate agent
        agent_name, agent = self.route(request)

        # Build messages
        messages = conversation_history or []
        messages.append({"role": "user", "content": request})

        # Invoke the agent
        result = agent.invoke(messages)

        # Add routing metadata
        result["routed_to"] = agent_name
        result["request"] = request

        return result

    async def ainvoke(self, request: str, conversation_history: list[dict] = None) -> dict:
        """Async version of invoke."""
        agent_name, agent = self.route(request)

        messages = conversation_history or []
        messages.append({"role": "user", "content": request})

        result = await agent.ainvoke(messages)

        result["routed_to"] = agent_name
        result["request"] = request

        return result

    def multi_agent_task(self, request: str, agents_needed: list[str]) -> dict:
        """Execute a task that requires multiple agents.

        Args:
            request: The original request
            agents_needed: List of agent names to involve

        Returns:
            Combined results from all agents
        """
        results = {}

        for agent_name in agents_needed:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                messages = [{"role": "user", "content": request}]

                # Add context from previous agents
                if results:
                    context = "Previous agents have provided the following context:\n"
                    for prev_agent, prev_result in results.items():
                        context += f"\n[{prev_agent}]: {prev_result.get('content', '')[:500]}...\n"
                    messages.insert(0, {"role": "user", "content": context})

                results[agent_name] = agent.invoke(messages)

        return {
            "agents_used": agents_needed,
            "results": results,
        }

    def get_agent_descriptions(self) -> str:
        """Get descriptions of all available agents."""
        descriptions = []
        for name, agent in self.agents.items():
            descriptions.append(f"**{name.title()}**: {agent.description}")
        return "\n".join(descriptions)

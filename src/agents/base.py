"""Base agent class with multi-provider LLM support."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import BaseTool

from ..config import get_config
from ..providers import create_llm


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    def __init__(
        self,
        name: str,
        description: str,
        tools: list[BaseTool],
        system_prompt: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.tools = tools
        self._system_prompt = system_prompt

        # Create LLM using the factory (supports Anthropic, OpenAI, Ollama)
        self.llm = create_llm()

        # Bind tools to the LLM
        if tools:
            self.llm_with_tools = self.llm.bind_tools(tools)
        else:
            self.llm_with_tools = self.llm

    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        if self._system_prompt:
            return self._system_prompt
        return self._default_system_prompt()

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return the default system prompt for this agent type."""
        pass

    def invoke(self, messages: list[dict], **kwargs) -> dict:
        """Invoke the agent with messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional arguments passed to the LLM

        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        # Convert to LangChain messages
        lc_messages = [SystemMessage(content=self.system_prompt)]

        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        # Invoke the LLM
        response = self.llm_with_tools.invoke(lc_messages, **kwargs)

        # Format response
        result = {
            "content": response.content,
            "agent": self.name,
        }

        if hasattr(response, "tool_calls") and response.tool_calls:
            result["tool_calls"] = response.tool_calls

        return result

    async def ainvoke(self, messages: list[dict], **kwargs) -> dict:
        """Async version of invoke."""
        lc_messages = [SystemMessage(content=self.system_prompt)]

        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        response = await self.llm_with_tools.ainvoke(lc_messages, **kwargs)

        result = {
            "content": response.content,
            "agent": self.name,
        }

        if hasattr(response, "tool_calls") and response.tool_calls:
            result["tool_calls"] = response.tool_calls

        return result

    def run_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to pass to the tool

        Returns:
            Tool execution result as string
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.invoke(tool_args)

        return f"Error: Tool '{tool_name}' not found"

    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of available tools."""
        if not self.tools:
            return "No tools available."

        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.name}: {tool.description}")

        return "\n".join(descriptions)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tools={len(self.tools)})"

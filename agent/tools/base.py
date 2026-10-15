"""Base tool abstractions and registry for the AI Agent."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool action."""
        pass


class ToolRegistry:
    """Registry managing available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}

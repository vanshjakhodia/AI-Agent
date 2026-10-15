"""Factory for creating LLM clients based on configuration."""

from __future__ import annotations
from agent.config import config
from agent.llm.base import BaseLLMClient
from agent.llm.gemini_client import GeminiLLMClient
from agent.llm.openai_client import OpenAILLMClient
from agent.llm.rule_planner import RuleBasedPlanner


def get_llm_client() -> BaseLLMClient:
    """Instantiate the appropriate LLM client based on configuration and available API keys."""
    provider = config.llm_provider.lower()

    if provider == "gemini":
        return GeminiLLMClient(api_key=config.gemini_api_key, model=config.llm_model)

    if provider == "openai":
        return OpenAILLMClient(api_key=config.openai_api_key, model=config.llm_model)

    # Auto mode: check keys
    if config.gemini_api_key:
        return GeminiLLMClient(api_key=config.gemini_api_key, model=config.llm_model)

    if config.openai_api_key:
        return OpenAILLMClient(api_key=config.openai_api_key, model=config.llm_model)

    # Default to robust built-in rule planner
    return RuleBasedPlanner()

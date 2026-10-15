"""Abstract Base Class and schemas for LLM Reasoning and Planning."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class LLMPlan:
    intent: str  # "compose_email", "confirm_send", "reject_send", "provide_contact", "list_contacts", "view_history", "execute_code", "web_search", "document_ops", "task_ops", "chat"
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: str = "professional"
    reuse_context: bool = False
    reasoning: str = ""
    raw_response: Optional[str] = None
    code: Optional[str] = None
    expression: Optional[str] = None
    query: Optional[str] = None
    doc_action: Optional[str] = None
    doc_path: Optional[str] = None
    doc_content: Optional[str] = None
    task_action: Optional[str] = None
    task_objective: Optional[str] = None
    task_steps: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "body": self.body,
            "tone": self.tone,
            "reuse_context": self.reuse_context,
            "reasoning": self.reasoning,
            "code": self.code,
            "expression": self.expression,
            "query": self.query,
            "doc_action": self.doc_action,
            "doc_path": self.doc_path,
            "doc_content": self.doc_content,
            "task_action": self.task_action,
            "task_objective": self.task_objective,
            "task_steps": self.task_steps,
        }



class BaseLLMClient(ABC):
    """Abstract interface for LLM Reasoning providers."""

    @abstractmethod
    def plan(
        self,
        user_input: str,
        conversation_history: str = "",
        last_draft: Optional[Dict[str, Any]] = None,
        contacts_summary: str = "",
    ) -> LLMPlan:
        """Analyze user input and produce a structured execution plan."""
        pass

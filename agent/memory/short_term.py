"""Short-term conversational memory and state tracking."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from agent.models import ConversationTurn, EmailDraft, SentRecord


class ShortTermMemory:
    """Maintains active dialogue turns, working context, and pending safety actions."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.last_draft: Optional[EmailDraft] = None
        self.pending_draft: Optional[EmailDraft] = None
        self.last_sent: Optional[SentRecord] = None
        self.pending_missing_contact_name: Optional[str] = None
        self.active_context: Dict[str, Any] = {}

    def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        turn = ConversationTurn(role=role, content=content, metadata=metadata or {})
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def set_pending_draft(self, draft: EmailDraft) -> None:
        self.pending_draft = draft
        self.last_draft = draft

    def clear_pending_draft(self) -> None:
        self.pending_draft = None

    def record_sent(self, record: SentRecord) -> None:
        self.last_sent = record
        self.pending_draft = None

    def set_missing_contact_name(self, name: Optional[str]) -> None:
        self.pending_missing_contact_name = name

    def get_last_draft(self) -> Optional[EmailDraft]:
        return self.last_draft

    def get_conversation_history_text(self) -> str:
        lines = []
        for turn in self.turns[-10:]:
            lines.append(f"{turn.role.capitalize()}: {turn.content}")
        return "\n".join(lines)

    def reset_working_state(self) -> None:
        self.pending_draft = None
        self.pending_missing_contact_name = None

    def clear_all(self) -> None:
        self.turns.clear()
        self.last_draft = None
        self.pending_draft = None
        self.last_sent = None
        self.pending_missing_contact_name = None
        self.active_context.clear()

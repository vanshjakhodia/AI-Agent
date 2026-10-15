"""Data models and schemas for the Autonomous AI Agent."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class DraftStatus(str, Enum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    SENT = "sent"
    CANCELLED = "cancelled"


class AgentLifecycleState(str, Enum):
    IDLE = "idle"
    AWAITING_CONTACT_INFO = "awaiting_contact_info"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    ERROR = "error"


class ToneType(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    URGENT = "urgent"
    FRIENDLY = "friendly"
    FORMAL = "formal"


@dataclass
class Contact:
    name: str
    email: str
    id: str = field(default_factory=lambda: f"c_{uuid.uuid4().hex[:8]}")
    aliases: List[str] = field(default_factory=list)
    role: Optional[str] = None
    organization: Optional[str] = None
    notes: Optional[str] = None

    def matches(self, query: str) -> bool:
        """Check if query matches name, email, or any aliases (case-insensitive)."""
        q = query.strip().lower()
        if not q:
            return False
        if q == self.email.lower() or q in self.name.lower():
            return True
        for alias in self.aliases:
            if q == alias.lower() or alias.lower() in q:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "aliases": self.aliases,
            "role": self.role,
            "organization": self.organization,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Contact:
        return cls(
            id=data.get("id", f"c_{uuid.uuid4().hex[:8]}"),
            name=data["name"],
            email=data["email"],
            aliases=data.get("aliases", []),
            role=data.get("role"),
            organization=data.get("organization"),
            notes=data.get("notes"),
        )


@dataclass
class EmailDraft:
    recipient_name: str
    recipient_email: str
    subject: str
    body: str
    tone: ToneType = ToneType.PROFESSIONAL
    draft_id: str = field(default_factory=lambda: f"draft_{uuid.uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: DraftStatus = DraftStatus.DRAFT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "body": self.body,
            "tone": self.tone.value if isinstance(self.tone, ToneType) else str(self.tone),
            "created_at": self.created_at,
            "status": self.status.value if isinstance(self.status, DraftStatus) else str(self.status),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmailDraft:
        tone_val = data.get("tone", ToneType.PROFESSIONAL.value)
        try:
            tone = ToneType(tone_val)
        except ValueError:
            tone = ToneType.PROFESSIONAL

        status_val = data.get("status", DraftStatus.DRAFT.value)
        try:
            status = DraftStatus(status_val)
        except ValueError:
            status = DraftStatus.DRAFT

        return cls(
            draft_id=data.get("draft_id", f"draft_{uuid.uuid4().hex[:8]}"),
            recipient_name=data["recipient_name"],
            recipient_email=data["recipient_email"],
            subject=data["subject"],
            body=data["body"],
            tone=tone,
            created_at=data.get("created_at", datetime.now().isoformat()),
            status=status,
        )


@dataclass
class SentRecord:
    record_id: str
    draft_id: str
    recipient_name: str
    recipient_email: str
    subject: str
    body: str
    sent_at: str
    status: str
    is_dry_run: bool = False
    message_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "draft_id": self.draft_id,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "subject": self.subject,
            "body": self.body,
            "sent_at": self.sent_at,
            "status": self.status,
            "is_dry_run": self.is_dry_run,
            "message_id": self.message_id,
            "error": self.error,
        }


@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    message: str
    state: AgentLifecycleState
    draft: Optional[EmailDraft] = None
    action_taken: Optional[str] = None
    requires_confirmation: bool = False
    sent_record: Optional[SentRecord] = None
    tool_output: Optional[Dict[str, Any]] = None
    task_record: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "state": self.state.value if isinstance(self.state, AgentLifecycleState) else str(self.state),
            "draft": self.draft.to_dict() if self.draft else None,
            "action_taken": self.action_taken,
            "requires_confirmation": self.requires_confirmation,
            "sent_record": self.sent_record.to_dict() if self.sent_record else None,
            "tool_output": self.tool_output,
            "task_record": self.task_record,
        }


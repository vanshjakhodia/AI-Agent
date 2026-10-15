"""Unit tests for Short-Term Memory and Context Reuse."""

from agent.memory.short_term import ShortTermMemory
from agent.models import EmailDraft, ToneType, DraftStatus


def test_short_term_memory_turns():
    mem = ShortTermMemory(max_turns=5)
    mem.add_turn("user", "Hello agent")
    mem.add_turn("assistant", "Hello! How can I help?")

    history = mem.get_conversation_history_text()
    assert "User: Hello agent" in history
    assert "Assistant: Hello! How can I help?" in history


def test_draft_caching_and_retrieval():
    mem = ShortTermMemory()
    draft = EmailDraft(
        recipient_name="John Doe",
        recipient_email="john.doe@example.com",
        subject="Meeting at 10 AM",
        body="Reminder about our 10 AM sync.",
        tone=ToneType.PROFESSIONAL,
    )
    mem.set_pending_draft(draft)

    retrieved = mem.get_last_draft()
    assert retrieved is not None
    assert retrieved.subject == "Meeting at 10 AM"
    assert retrieved.recipient_name == "John Doe"

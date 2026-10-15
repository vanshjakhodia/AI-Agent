"""Integration tests for AI Agent Orchestrator covering all experiment requirements."""

import tempfile
from pathlib import Path
import pytest

from agent.orchestrator import AIAgent
from agent.config import AgentConfig
from agent.models import AgentLifecycleState, DraftStatus


@pytest.fixture
def agent_instance():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        cfg = AgentConfig(
            data_dir=base / "data",
            contacts_file=base / "contacts.json",
            audit_file=base / "audit.json",
            outbox_dir=base / "outbox",
            dry_run=True,
            require_confirmation=True,
        )
        agent = AIAgent(cfg=cfg)
        yield agent


def test_full_agent_workflow(agent_instance):
    agent = agent_instance

    # Turn 1: Initial meeting reminder instruction
    r1 = agent.process("Send an email to John reminding him about tomorrow's 10 AM meeting")
    assert r1.state == AgentLifecycleState.AWAITING_CONFIRMATION
    assert r1.requires_confirmation is True
    assert r1.draft is not None
    assert r1.draft.recipient_name == "John Doe"
    assert r1.draft.recipient_email == "john.doe@example.com"
    assert "10" in r1.draft.subject or "Meeting" in r1.draft.subject

    # Turn 2: User confirms -> Email sent via tool
    r2 = agent.process("yes")
    assert r2.state == AgentLifecycleState.IDLE
    assert r2.action_taken == "email_sent"
    assert r2.sent_record is not None
    assert r2.sent_record.recipient_email == "john.doe@example.com"

    # Turn 3: Follow-up command reusing memory: "Send the same email to Sarah too"
    r3 = agent.process("Send the same email to Sarah too")
    assert r3.state == AgentLifecycleState.AWAITING_CONFIRMATION
    assert r3.draft is not None
    assert r3.draft.recipient_name == "Sarah Connor"
    assert r3.draft.recipient_email == "sarah.connor@example.com"
    # Subject and body must be inherited from previous draft
    assert r3.draft.subject == r1.draft.subject
    assert "Sarah" in r3.draft.body

    # Turn 4: User confirms Sarah's email
    r4 = agent.process("confirm")
    assert r4.state == AgentLifecycleState.IDLE
    assert r4.action_taken == "email_sent"
    assert r4.sent_record.recipient_email == "sarah.connor@example.com"

    # Turn 5: Email to Dr. Kunal Meher submitting assignment
    r5 = agent.process("Send an email to Dr. Kunal Meher submitting my Experiment 9 AI Agent assignment")
    assert r5.state == AgentLifecycleState.AWAITING_CONFIRMATION
    assert r5.draft is not None
    assert r5.draft.recipient_email == "kunal.meher@atlasuniversity.edu.in"
    assert "Experiment 9" in r5.draft.subject

    # Turn 6: Confirm submission
    r6 = agent.process("yes")
    assert r6.state == AgentLifecycleState.IDLE
    assert r6.action_taken == "email_sent"
    assert r6.sent_record.recipient_email == "kunal.meher@atlasuniversity.edu.in"

    # Turn 7: Test anti-hallucination guardrail with unknown contact
    r7 = agent.process("Send an email to Bob about the product launch")
    assert r7.state == AgentLifecycleState.AWAITING_CONTACT_INFO
    assert "Anti-Hallucination Guardrail" in r7.message

    # Turn 8: Provide Bob's email address
    r8 = agent.process("his email is bob@acme.org")
    assert r8.state == AgentLifecycleState.AWAITING_CONFIRMATION
    assert r8.draft is not None
    assert r8.draft.recipient_email == "bob@acme.org"

    # Turn 9: User rejects / cancels
    r9 = agent.process("no")
    assert r9.state == AgentLifecycleState.IDLE
    assert r9.action_taken == "draft_cancelled"
    assert agent.short_term_memory.pending_draft is None

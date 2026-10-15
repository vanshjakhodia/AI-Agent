"""Unit tests for Safety Guardrails and Human-in-the-loop policies."""

from agent.tools.guardrail_tool import SafetyGuardrailTool


def test_guardrail_blocks_unconfirmed_email():
    guard = SafetyGuardrailTool(require_confirmation=True)
    res = guard.run(action_type="send_email", user_confirmed=False)
    assert res["allowed"] is False
    assert "Explicit user confirmation is strictly required" in res["reason"]


def test_guardrail_allows_confirmed_email():
    guard = SafetyGuardrailTool(require_confirmation=True)
    res = guard.run(action_type="send_email", user_confirmed=True)
    assert res["allowed"] is True


def test_guardrail_allows_when_confirmation_disabled():
    guard = SafetyGuardrailTool(require_confirmation=False)
    res = guard.run(action_type="send_email", user_confirmed=False)
    assert res["allowed"] is True

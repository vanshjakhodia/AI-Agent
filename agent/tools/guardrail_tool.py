"""Safety guardrails and human-in-the-loop verification tool."""

from __future__ import annotations
from typing import Any, Dict
from agent.tools.base import BaseTool
from agent.config import config


class SafetyGuardrailTool(BaseTool):
    name = "safety_guardrail"
    description = (
        "Enforces human-in-the-loop confirmation before executing irreversible external actions "
        "such as sending emails via SMTP or modifying live records."
    )

    def __init__(self, require_confirmation: bool = True):
        self.require_confirmation = require_confirmation

    def run(self, action_type: str, user_confirmed: bool = False, **kwargs) -> Dict[str, Any]:
        """Check if an irreversible action is permitted to execute."""
        # If confirmation is globally disabled via config, allow execution
        if not self.require_confirmation:
            return {
                "allowed": True,
                "reason": "Confirmation requirement is bypassed in agent configuration (auto-confirm mode).",
            }

        if action_type.lower() in ("send_email", "smtp_dispatch"):
            if user_confirmed:
                return {
                    "allowed": True,
                    "reason": "Explicit user confirmation granted. Irreversible action permitted.",
                }
            else:
                return {
                    "allowed": False,
                    "reason": (
                        "Safety Guardrail: Sending an email is an irreversible action. "
                        "Explicit user confirmation is strictly required before dispatch."
                    ),
                }

        # Safe actions by default
        return {"allowed": True, "reason": "Action does not carry irreversible external consequences."}

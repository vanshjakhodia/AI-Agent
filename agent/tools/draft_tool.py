"""Email drafting and content validation tool."""

from __future__ import annotations
import re
from typing import Any, Dict, Optional
from agent.tools.base import BaseTool
from agent.models import EmailDraft, ToneType, DraftStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class DraftEmailTool(BaseTool):
    name = "draft_email"
    description = "Creates a structured and validated email draft ready for safety review."

    def run(
        self,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        body: str,
        tone: str = "professional",
        **kwargs,
    ) -> Dict[str, Any]:
        if not recipient_email or not EMAIL_REGEX.match(recipient_email.strip()):
            return {
                "success": False,
                "error": f"Invalid recipient email address: '{recipient_email}'",
            }

        if not subject or not subject.strip():
            return {"success": False, "error": "Subject cannot be empty"}

        if not body or not body.strip():
            return {"success": False, "error": "Email body cannot be empty"}

        try:
            tone_enum = ToneType(tone.lower())
        except ValueError:
            tone_enum = ToneType.PROFESSIONAL

        draft = EmailDraft(
            recipient_name=recipient_name.strip(),
            recipient_email=recipient_email.strip().lower(),
            subject=subject.strip(),
            body=body.strip(),
            tone=tone_enum,
            status=DraftStatus.PENDING_CONFIRMATION,
        )

        return {
            "success": True,
            "draft": draft.to_dict(),
            "message": f"Draft created for {draft.recipient_name} <{draft.recipient_email}> with subject: '{draft.subject}'",
        }

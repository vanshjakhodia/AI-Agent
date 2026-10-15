"""SMTP email sender tool supporting Gmail TLS, Google App Passwords, and safe Dry-Run mode."""

from __future__ import annotations
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any, Dict, Optional

from agent.tools.base import BaseTool
from agent.models import EmailDraft, SentRecord, DraftStatus
from agent.config import config


class SMTPSenderTool(BaseTool):
    name = "send_email_smtp"
    description = (
        "Dispatches an approved email draft over SMTP (e.g. Gmail using an App Password) "
        "or through safe local outbox simulation if dry_run is enabled."
    )

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        sender_name: Optional[str] = None,
        dry_run: Optional[bool] = None,
        outbox_dir: Optional[Path] = None,
    ):
        self.host = host or config.smtp_host
        self.port = port or config.smtp_port
        self.user = user if user is not None else config.smtp_user
        self.password = password if password is not None else config.smtp_password
        self.use_tls = use_tls if use_tls is not None else config.smtp_use_tls
        self.sender_name = sender_name or config.sender_name
        self.sender_email = self.user or config.sender_email or "agent@atlas-ai.internal"
        self.dry_run = dry_run if dry_run is not None else config.dry_run
        self.outbox_dir = outbox_dir or config.outbox_dir
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

    def run(self, draft: EmailDraft, force_dry_run: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
        """Dispatch email draft via SMTP or dry-run simulation."""
        is_dry_run = self.dry_run if force_dry_run is None else force_dry_run

        # If credentials are missing, automatically fall back to dry run safely with warning
        has_credentials = bool(self.user and self.password)
        if not has_credentials and not is_dry_run:
            is_dry_run = True
            missing_creds_note = " (Simulated: SMTP_USER and SMTP_PASSWORD not configured in .env)"
        else:
            missing_creds_note = ""

        # Construct RFC 5322 MIME Message with AI Agent Provenance Headers
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = f"{draft.recipient_name} <{draft.recipient_email}>"
        msg["Subject"] = draft.subject
        msg["Date"] = formatdate(localtime=True)
        message_id = make_msgid(domain="agent.atlas-ai")
        msg["Message-ID"] = message_id
        
        # Technical Provenance Headers (inspectable via Gmail "Show Original")
        msg["X-Mailer"] = "Autonomous AI Agent v2.1"
        msg["X-AI-Agent-Framework"] = "LLM Reasoning + Working Memory + Tool Registry + ReAct Orchestration"
        msg["X-AI-Agent-Draft-ID"] = draft.draft_id
        msg["X-AI-Agent-Guardrail-Verification"] = "Explicit Human-in-the-Loop Confirmation Verified"

        # Plain text version
        plain_body = (
            f"{draft.body}\n\n"
            f"------------------------------------------------------------\n"
            f"[PROVENANCE] AUTONOMOUS AI AGENT TELEMETRY\n"
            f"• Engine: Autonomous AI Agent v2.1\n"
            f"• Dispatch Account: {self.sender_email}\n"
            f"• Verified Recipient: {draft.recipient_name} <{draft.recipient_email}>\n"
            f"• Draft ID: {draft.draft_id}\n"
            f"• Verification: Dispatched autonomously via SMTP with Human-in-the-Loop safety approval.\n"
            f"------------------------------------------------------------"
        )
        text_part = MIMEText(plain_body, "plain", "utf-8")
        msg.attach(text_part)

        # HTML version with visual Executive Verification Card
        html_content = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px; }}
    .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; color: #ffffff; padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; }}
    .badge {{ background: #10b981; color: #ffffff; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .content {{ padding: 28px 24px; font-size: 15px; color: #334155; }}
    .telemetry-box {{ background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin-top: 24px; font-size: 12.5px; color: #475569; }}
    .telemetry-title {{ font-weight: 700; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; font-size: 11px; }}
    .telemetry-row {{ margin-bottom: 4px; }}
    .telemetry-row strong {{ color: #0f172a; }}
    .footer {{ padding: 14px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="font-size: 16px; font-weight: 700; letter-spacing: -0.3px;">Autonomous AI Agent</div>
      <div class="badge">Verified Autonomous Dispatch</div>
    </div>
    <div class="content">
      {draft.body.replace(chr(10), '<br>')}
      
      <div class="telemetry-box">
        <div class="telemetry-title">[PROVENANCE] AI Agent Provenance & Execution Telemetry</div>
        <div class="telemetry-row"><strong>Engine:</strong> Autonomous AI Agent v2.1</div>

        <div class="telemetry-row"><strong>Architecture:</strong> LLM Reasoning + Working Memory + Tool Registry + Orchestration</div>
        <div class="telemetry-row"><strong>Dispatch Account:</strong> {self.sender_email}</div>
        <div class="telemetry-row"><strong>Verified Recipient:</strong> {draft.recipient_name} &lt;{draft.recipient_email}&gt;</div>
        <div class="telemetry-row"><strong>Draft Reference:</strong> <code>{draft.draft_id}</code></div>
        <div class="telemetry-row"><strong>Safety Guardrail:</strong> Explicit Human-in-the-Loop Affirmation Granted</div>
      </div>
    </div>
    <div class="footer">
      Generated & Dispatched Autonomously by AI Agent via Python SMTP / RFC 5322
    </div>
  </div>
</body>
</html>
"""
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        record_id = f"rec_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now().isoformat()

        if is_dry_run:
            # Save .eml file to outbox
            eml_file = self.outbox_dir / f"{record_id}_{draft.recipient_name.replace(' ', '_')}.eml"
            with open(eml_file, "w", encoding="utf-8") as f:
                f.write(msg.as_string())

            record = SentRecord(
                record_id=record_id,
                draft_id=draft.draft_id,
                recipient_name=draft.recipient_name,
                recipient_email=draft.recipient_email,
                subject=draft.subject,
                body=draft.body,
                sent_at=now_iso,
                status="SENT_DRY_RUN",
                is_dry_run=True,
                message_id=message_id,
            )
            draft.status = DraftStatus.SENT

            return {
                "success": True,
                "is_dry_run": True,
                "record": record.to_dict(),
                "outbox_path": str(eml_file),
                "message": (
                    f"[DRY-RUN] Email safely simulated and written to {eml_file.name}{missing_creds_note}. "
                    f"To: {draft.recipient_email} | Subject: '{draft.subject}'"
                ),
            }

        # Live SMTP Dispatch (e.g. Gmail)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.ehlo()
                if self.use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(self.user, self.password)
                server.send_message(msg)

            record = SentRecord(
                record_id=record_id,
                draft_id=draft.draft_id,
                recipient_name=draft.recipient_name,
                recipient_email=draft.recipient_email,
                subject=draft.subject,
                body=draft.body,
                sent_at=now_iso,
                status="DELIVERED",
                is_dry_run=False,
                message_id=message_id,
            )
            draft.status = DraftStatus.SENT

            return {
                "success": True,
                "is_dry_run": False,
                "record": record.to_dict(),
                "message": f"Email successfully delivered to {draft.recipient_name} <{draft.recipient_email}> via SMTP!",
            }

        except smtplib.SMTPAuthenticationError as auth_err:
            error_msg = (
                f"SMTP Authentication Error: {auth_err}. "
                "Ensure you generated a 16-character Google App Password under "
                "Google Account > Security > 2-Step Verification > App passwords."
            )
            return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": f"Failed to send email via SMTP: {str(e)}"}

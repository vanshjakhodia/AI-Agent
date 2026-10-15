"""Autonomous AI Agent Orchestrator.

Combines:
- LLM (Reasoning & Planning)
- Memory (Short-term conversation context + Long-term persistent contacts and audit log)
- Tools (Contact Lookup, Contact Add, Email Drafter, Safety Guardrails, SMTP Sender)
- Orchestration (ReAct-style state-machine loop with anti-hallucination & safety constraints)
"""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, List

from agent.config import config, AgentConfig
from agent.models import (
    AgentLifecycleState,
    AgentResult,
    EmailDraft,
    SentRecord,
    DraftStatus,
    ToneType,
)
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import ContactsStore, AuditLog
from agent.tools.contacts_tool import ContactLookupTool, ContactAddTool
from agent.tools.draft_tool import DraftEmailTool
from agent.tools.guardrail_tool import SafetyGuardrailTool
from agent.tools.smtp_tool import SMTPSenderTool
from agent.llm.base import BaseLLMClient, LLMPlan
from agent.llm.factory import get_llm_client

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class AIAgent:
    """Production-grade AI Email Agent with safety guardrails and anti-hallucination."""

    def __init__(
        self,
        cfg: Optional[AgentConfig] = None,
        llm_client: Optional[BaseLLMClient] = None,
        contacts_store: Optional[ContactsStore] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.config = cfg or config
        self.state = AgentLifecycleState.IDLE

        # 1. Memory Subsystem
        self.short_term_memory = ShortTermMemory()
        self.contacts_store = contacts_store or ContactsStore(self.config.contacts_file)
        self.audit_log = audit_log or AuditLog(self.config.audit_file)

        # 2. Tools Subsystem
        self.lookup_tool = ContactLookupTool(self.contacts_store)
        self.add_contact_tool = ContactAddTool(self.contacts_store)
        self.draft_tool = DraftEmailTool()
        self.guardrail_tool = SafetyGuardrailTool(require_confirmation=self.config.require_confirmation)
        self.smtp_tool = SMTPSenderTool(
            host=self.config.smtp_host,
            port=self.config.smtp_port,
            user=self.config.smtp_user,
            password=self.config.smtp_password,
            use_tls=self.config.smtp_use_tls,
            sender_name=self.config.sender_name,
            dry_run=self.config.dry_run,
            outbox_dir=self.config.outbox_dir,
        )

        # 3. LLM Reasoning Subsystem
        self.llm = llm_client or get_llm_client()

    def process(self, user_input: str) -> AgentResult:
        """Main agent processing turn: perceive, reason, plan, act, and remember."""
        user_input_clean = user_input.strip()
        self.short_term_memory.add_turn("user", user_input_clean)

        # Handle state: Awaiting Missing Contact Email
        if self.state == AgentLifecycleState.AWAITING_CONTACT_INFO and self.short_term_memory.pending_missing_contact_name:
            return self._handle_provided_missing_contact(user_input_clean)

        # Get LLM Reasoning & Plan
        contacts_summary = ", ".join(f"{c.name} <{c.email}>" for c in self.contacts_store.list_all())
        last_draft_dict = self.short_term_memory.get_last_draft().to_dict() if self.short_term_memory.get_last_draft() else None
        history_text = self.short_term_memory.get_conversation_history_text()

        plan: LLMPlan = self.llm.plan(
            user_input=user_input_clean,
            conversation_history=history_text,
            last_draft=last_draft_dict,
            contacts_summary=contacts_summary,
        )

        # Route based on detected intent
        if plan.intent == "confirm_send":
            return self._handle_confirmation()

        if plan.intent == "reject_send":
            return self._handle_rejection()

        if plan.intent == "list_contacts":
            return self._handle_list_contacts()

        if plan.intent == "view_history":
            return self._handle_view_history()

        if plan.intent == "provide_contact" and self.state == AgentLifecycleState.AWAITING_CONTACT_INFO:
            return self._handle_provided_missing_contact(user_input_clean)

        if plan.intent == "compose_email":
            return self._handle_compose_email(plan)

        # Default fallback / Help
        help_msg = (
            "I am your autonomous Email Agent. Here is what I can do:\n"
            "• Draft and send emails: e.g. \"Send an email to John reminding him about tomorrow's 10 AM meeting\"\n"
            "• Submit assignments: e.g. \"Send an email to Dr. Kunal Meher submitting my Experiment 9 AI Agent assignment\"\n"
            "• Reuse context: e.g. \"Send the same email to Sarah too\"\n"
            "• View contacts: \"Show contacts\"\n"
            "• View sent history: \"View history\"\n\n"
            "How may I assist you?"
        )
        self.state = AgentLifecycleState.IDLE
        self.short_term_memory.add_turn("assistant", help_msg)
        return AgentResult(message=help_msg, state=self.state)

    def _handle_compose_email(self, plan: LLMPlan) -> AgentResult:
        """Executes entity resolution, anti-hallucination lookup, drafting, and guardrail check."""
        recipient_name = plan.recipient_name or ""
        recipient_email = plan.recipient_email

        # If user asked to reuse context ("send the same email to Sarah too")
        if plan.reuse_context:
            last_draft = self.short_term_memory.get_last_draft()
            if not last_draft:
                err_msg = "You asked to send the same email, but there is no previous email in memory. Please specify the email content."
                self.short_term_memory.add_turn("assistant", err_msg)
                return AgentResult(message=err_msg, state=AgentLifecycleState.IDLE)

            subject = last_draft.subject
            # Tailor salutation if target recipient is different
            body = last_draft.body
            if recipient_name and last_draft.recipient_name:
                body = re.sub(
                    rf"\b(Dear|Hi|Hello)\s+{re.escape(last_draft.recipient_name)}\b",
                    rf"\1 {recipient_name}",
                    body,
                    flags=re.IGNORECASE,
                )
            tone = last_draft.tone.value if isinstance(last_draft.tone, ToneType) else str(last_draft.tone)
        else:
            subject = plan.subject or "Important Update"
            body = plan.body or "Please review the attached communication."
            tone = plan.tone or "professional"

        # Anti-Hallucination Guardrail: Resolve email address strictly
        if not recipient_email:
            lookup_res = self.lookup_tool.run(query=recipient_name)
            if lookup_res.get("found"):
                recipient_email = lookup_res["contact"]["email"]
                recipient_name = lookup_res["contact"]["name"]
            else:
                # Contact NOT found! Refuse to hallucinate address. Ask user for information.
                self.state = AgentLifecycleState.AWAITING_CONTACT_INFO
                self.short_term_memory.set_missing_contact_name(recipient_name)
                # Store pending composition parameters in active context
                self.short_term_memory.active_context = {
                    "recipient_name": recipient_name,
                    "subject": subject,
                    "body": body,
                    "tone": tone,
                }
                ask_msg = (
                    f"⚠️ Anti-Hallucination Guardrail: I could not find '{recipient_name}' in your contacts address book.\n"
                    f"To prevent sending to an incorrect address, please provide {recipient_name}'s email address (e.g., username@domain.com)."
                )
                self.short_term_memory.add_turn("assistant", ask_msg)
                return AgentResult(message=ask_msg, state=self.state)

        # Create Email Draft
        draft_res = self.draft_tool.run(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            tone=tone,
        )

        if not draft_res.get("success"):
            err_msg = f"Failed to draft email: {draft_res.get('error')}"
            self.short_term_memory.add_turn("assistant", err_msg)
            return AgentResult(message=err_msg, state=AgentLifecycleState.ERROR)

        draft = EmailDraft.from_dict(draft_res["draft"])
        self.short_term_memory.set_pending_draft(draft)

        # Check safety guardrails
        guard_res = self.guardrail_tool.run(action_type="send_email", user_confirmed=False)

        if not guard_res["allowed"]:
            self.state = AgentLifecycleState.AWAITING_CONFIRMATION
            confirm_prompt = (
                f"📝 **Email Draft Prepared (Review & Confirmation Required)**\n\n"
                f"• **Recipient:** {draft.recipient_name} (`{draft.recipient_email}`)\n"
                f"• **Subject:** {draft.subject}\n"
                f"• **Tone:** {draft.tone.value if isinstance(draft.tone, ToneType) else draft.tone}\n\n"
                f"**Body Preview:**\n"
                f"```\n{draft.body}\n```\n\n"
                f"🛡️ **Safety Guardrail:** Sending an email is an irreversible action. "
                f"Would you like me to send this email now? Reply **'Yes'** to send or **'No'** to cancel."
            )
            self.short_term_memory.add_turn("assistant", confirm_prompt)
            return AgentResult(
                message=confirm_prompt,
                state=self.state,
                draft=draft,
                requires_confirmation=True,
                action_taken="draft_created",
            )

        # If confirmation is bypassed via config (auto-confirm mode)
        return self._execute_smtp_send(draft)

    def _handle_confirmation(self) -> AgentResult:
        """User gave explicit affirmative confirmation to dispatch the pending draft."""
        draft = self.short_term_memory.pending_draft
        if not draft:
            msg = "There is no pending email draft waiting for confirmation."
            self.short_term_memory.add_turn("assistant", msg)
            return AgentResult(message=msg, state=AgentLifecycleState.IDLE)

        # Safety guardrail check with user_confirmed=True
        guard_res = self.guardrail_tool.run(action_type="send_email", user_confirmed=True)
        if not guard_res["allowed"]:
            msg = f"Action blocked by safety policy: {guard_res['reason']}"
            self.short_term_memory.add_turn("assistant", msg)
            return AgentResult(message=msg, state=AgentLifecycleState.ERROR)

        return self._execute_smtp_send(draft)

    def _execute_smtp_send(self, draft: EmailDraft) -> AgentResult:
        """Dispatches the approved draft via SMTP sender tool."""
        self.state = AgentLifecycleState.EXECUTING
        smtp_res = self.smtp_tool.run(draft=draft)

        if not smtp_res.get("success"):
            self.state = AgentLifecycleState.ERROR
            err_msg = f"❌ Dispatch Failed: {smtp_res.get('error')}"
            self.short_term_memory.add_turn("assistant", err_msg)
            return AgentResult(message=err_msg, state=self.state, draft=draft)

        # Successfully sent or simulated dry-run
        record = SentRecord(
            record_id=smtp_res["record"]["record_id"],
            draft_id=draft.draft_id,
            recipient_name=draft.recipient_name,
            recipient_email=draft.recipient_email,
            subject=draft.subject,
            body=draft.body,
            sent_at=smtp_res["record"]["sent_at"],
            status=smtp_res["record"]["status"],
            is_dry_run=smtp_res.get("is_dry_run", False),
            message_id=smtp_res["record"].get("message_id"),
        )

        # Remember in short-term and long-term memory
        self.short_term_memory.record_sent(record)
        self.audit_log.record(record)
        self.state = AgentLifecycleState.IDLE

        success_msg = (
            f"✅ **Email Sent Successfully!**\n\n"
            f"• **Recipient:** {record.recipient_name} (`{record.recipient_email}`)\n"
            f"• **Subject:** {record.subject}\n"
            f"• **Status:** {record.status}\n"
            f"• **Mode:** {'Simulated Dry-Run (Written to Outbox)' if record.is_dry_run else 'Live SMTP Delivery'}\n"
            f"• **Message-ID:** `{record.message_id}`\n\n"
            f"{smtp_res.get('message', '')}"
        )
        self.short_term_memory.add_turn("assistant", success_msg)
        return AgentResult(
            message=success_msg,
            state=self.state,
            draft=draft,
            sent_record=record,
            action_taken="email_sent",
        )

    def _handle_rejection(self) -> AgentResult:
        """User cancelled or declined the pending draft."""
        draft = self.short_term_memory.pending_draft
        if draft:
            draft.status = DraftStatus.CANCELLED
            self.short_term_memory.clear_pending_draft()

        self.state = AgentLifecycleState.IDLE
        cancel_msg = "🛑 Action cancelled. The email draft has been discarded and no email was sent."
        self.short_term_memory.add_turn("assistant", cancel_msg)
        return AgentResult(message=cancel_msg, state=self.state, action_taken="draft_cancelled")

    def _handle_provided_missing_contact(self, user_input: str) -> AgentResult:
        """Processes user response providing the missing contact email."""
        found_emails = EMAIL_REGEX.findall(user_input)
        missing_name = self.short_term_memory.pending_missing_contact_name or "Contact"

        if not found_emails:
            retry_msg = (
                f"I could not detect a valid email address in '{user_input}'. "
                f"Please provide a valid email format for {missing_name} (e.g. name@domain.com) or type 'cancel'."
            )
            self.short_term_memory.add_turn("assistant", retry_msg)
            return AgentResult(message=retry_msg, state=self.state)

        email = found_emails[0].lower()
        # Add to contacts store
        add_res = self.add_contact_tool.run(
            name=missing_name,
            email=email,
            notes="Added dynamically during conversation flow",
        )

        # Retrieve saved context to resume drafting
        ctx = self.short_term_memory.active_context or {}
        subject = ctx.get("subject", "Important Update")
        body = ctx.get("body", "Please see the following update.")
        tone = ctx.get("tone", "professional")

        # Clear missing contact state
        self.short_term_memory.set_missing_contact_name(None)
        self.short_term_memory.active_context.clear()

        # Resume drafting
        resume_plan = LLMPlan(
            intent="compose_email",
            recipient_name=missing_name,
            recipient_email=email,
            subject=subject,
            body=body,
            tone=tone,
            reuse_context=False,
            reasoning=f"Resolved missing email {email} for {missing_name}. Resuming drafting.",
        )
        return self._handle_compose_email(resume_plan)

    def _handle_list_contacts(self) -> AgentResult:
        contacts = self.contacts_store.list_all()
        if not contacts:
            msg = "Your contacts store is currently empty."
        else:
            lines = ["📖 **Contacts Address Book:**"]
            for c in contacts:
                role_str = f" ({c.role})" if c.role else ""
                lines.append(f"• **{c.name}**{role_str}: `{c.email}`")
            msg = "\n".join(lines)

        self.state = AgentLifecycleState.IDLE
        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(message=msg, state=self.state, action_taken="list_contacts")

    def _handle_view_history(self) -> AgentResult:
        recent = self.audit_log.get_recent(5)
        if not recent:
            msg = "No emails have been sent yet."
        else:
            lines = ["📜 **Recent Sent Emails Audit Log:**"]
            for r in reversed(recent):
                mode_tag = "[Dry-Run]" if r.is_dry_run else "[Live]"
                lines.append(f"• {mode_tag} **{r.sent_at[:19]}** to **{r.recipient_name}** (`{r.recipient_email}`)\n  Subject: *{r.subject}*")
            msg = "\n".join(lines)

        self.state = AgentLifecycleState.IDLE
        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(message=msg, state=self.state, action_taken="view_history")

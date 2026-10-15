"""Autonomous AI Agent Orchestrator.

Governed by the Master System Prompt across all 9 domains:
- General Intelligence
- Research & Web Intelligence
- Programming & Software Development (Code execution & verification)
- Business & Productivity (Email communications & structured reporting)
- Documents & Knowledge (Workspace file reading, writing, searching)
- Personal Assistance (Reminders & schedules)
- Creative Work (Presentations, design concepts, storytelling)
- Data & Decision Support (Calculations, analysis, tables)
- Automation & Task Tracking (Section 9 Task Records & 8-step operating cycle)

Strictly adheres to:
- Operating principles (8-step execution loop)
- Safety guardrails (Zero unauthorized irreversible actions)
- Anti-hallucination policies
- Zero-emoji professional interface
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
from agent.tools.code_exec_tool import CodeExecutionTool
from agent.tools.web_search_tool import WebSearchTool
from agent.tools.document_tool import DocumentTool
from agent.tools.task_manager_tool import TaskManagerTool, TaskRecord, TaskStatus
from agent.llm.base import BaseLLMClient, LLMPlan
from agent.llm.factory import get_llm_client

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class AIAgent:
    """Production-grade Autonomous AI Agent with multi-domain tools and safety guardrails."""

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
        self.code_tool = CodeExecutionTool()
        self.web_tool = WebSearchTool()
        self.doc_tool = DocumentTool()
        self.task_tool = TaskManagerTool()

        # 3. LLM Reasoning Subsystem
        self.llm = llm_client or get_llm_client()

    def process(self, user_input: str) -> AgentResult:
        """Main agent operating turn executing the 8-step cycle."""
        user_input_clean = user_input.strip()
        self.short_term_memory.add_turn("user", user_input_clean)

        # Handle state: Awaiting Missing Contact Email
        if self.state == AgentLifecycleState.AWAITING_CONTACT_INFO and self.short_term_memory.pending_missing_contact_name:
            return self._handle_provided_missing_contact(user_input_clean)

        # Step 1 & 2: Perceive, Understand & Assess via LLM / Deterministic Planner
        contacts_summary = ", ".join(f"{c.name} <{c.email}>" for c in self.contacts_store.list_all())
        last_draft_dict = self.short_term_memory.get_last_draft().to_dict() if self.short_term_memory.get_last_draft() else None
        history_text = self.short_term_memory.get_conversation_history_text()

        plan: LLMPlan = self.llm.plan(
            user_input=user_input_clean,
            conversation_history=history_text,
            last_draft=last_draft_dict,
            contacts_summary=contacts_summary,
        )

        # Step 3, 4, 5: Plan, Select Tools & Execute
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

        if plan.intent == "execute_code":
            return self._handle_execute_code(plan)

        if plan.intent == "web_search":
            return self._handle_web_search(plan)

        if plan.intent == "document_ops":
            return self._handle_document_ops(plan)

        if plan.intent == "task_ops":
            return self._handle_task_ops(plan)

        if plan.intent == "compose_email":
            return self._handle_compose_email(plan)

        # Default fallback / General intelligence
        return self._handle_general_query(user_input_clean)

    def _handle_execute_code(self, plan: LLMPlan) -> AgentResult:
        """Executes code or evaluates mathematical expressions via CodeExecutionTool."""
        self.state = AgentLifecycleState.EXECUTING
        res = self.code_tool.run(code=plan.code or "", expression=plan.expression or "")
        self.state = AgentLifecycleState.IDLE

        if res.get("success"):
            if "expression" in res:
                out_msg = (
                    f"**Mathematical Evaluation Result:**\n\n"
                    f"• **Expression:** `{res.get('expression')}`\n"
                    f"• **Computed Value:** `{res.get('result')}`\n"
                    f"• **Execution Duration:** {res.get('duration_seconds')}s"
                )
            else:
                out_msg = (
                    f"**Code Execution Successful:**\n\n"
                    f"```python\n{res.get('code')}\n```\n\n"
                    f"**Output (stdout):**\n"
                    f"```\n{res.get('stdout')}\n```\n"
                    f"• **Exit Code:** {res.get('exit_code')}\n"
                    f"• **Duration:** {res.get('duration_seconds')}s"
                )
        else:
            out_msg = (
                f"**Code Execution Error:**\n\n"
                f"• **Error Message:** {res.get('error')}\n"
                f"```\n{res.get('stderr')}\n```"
            )

        self.short_term_memory.add_turn("assistant", out_msg)
        return AgentResult(
            message=out_msg,
            state=self.state,
            action_taken="code_execution",
            tool_output=res,
        )

    def _handle_web_search(self, plan: LLMPlan) -> AgentResult:
        """Performs web research and synthesizes verified sources."""
        self.state = AgentLifecycleState.EXECUTING
        query = plan.query or "General AI Agent Research"
        res = self.web_tool.run(query=query)
        self.state = AgentLifecycleState.IDLE

        lines = [
            f"**Research Results for:** \"{query}\"\n",
            f"**Sources Found:** {res.get('count', 0)}\n",
        ]
        for idx, item in enumerate(res.get("results", []), 1):
            lines.append(f"{idx}. **{item.get('title')}**")
            lines.append(f"   URL: {item.get('url')}")
            lines.append(f"   Summary: {item.get('snippet')}\n")

        msg = "\n".join(lines)
        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(
            message=msg,
            state=self.state,
            action_taken="web_search",
            tool_output=res,
        )

    def _handle_document_ops(self, plan: LLMPlan) -> AgentResult:
        """Performs local document management operations."""
        self.state = AgentLifecycleState.EXECUTING
        action = plan.doc_action or "list"
        res = self.doc_tool.run(
            action=action,
            file_path=plan.doc_path or "",
            content=plan.doc_content or "",
            query=plan.query or "",
        )
        self.state = AgentLifecycleState.IDLE

        if not res.get("success"):
            msg = f"**Document Operation Failed:** {res.get('error')}"
        elif action == "read":
            msg = (
                f"**File Content: `{res.get('file_path')}`** ({res.get('lines_count')} lines, {res.get('size_bytes')} bytes)\n\n"
                f"```\n{res.get('content')}\n```"
            )
        elif action == "write":
            msg = f"**File Written Successfully:** `{res.get('file_path')}` ({res.get('bytes_written')} bytes)."
        elif action == "list":
            lines = [f"**Workspace Directory: `{res.get('directory')}`** ({res.get('count')} items)\n"]
            for item in res.get("items", []):
                kind = "Directory" if item["is_dir"] else f"File ({item['size']} B)"
                lines.append(f"• `{item['name']}` — {kind}")
            msg = "\n".join(lines)
        elif action == "search":
            lines = [f"**Search Matches for \"{res.get('query')}\":** ({res.get('count')} files)\n"]
            for m in res.get("matches", []):
                lines.append(f"• `{m['file']}` ({m['occurrences']} occurrences)")
            msg = "\n".join(lines)
        else:
            msg = f"Document action '{action}' completed."

        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(
            message=msg,
            state=self.state,
            action_taken="document_operation",
            tool_output=res,
        )

    def _handle_task_ops(self, plan: LLMPlan) -> AgentResult:
        """Manages structured Section 9 Task Records."""
        action = plan.task_action or "get"
        res = self.task_tool.run(
            action=action,
            objective=plan.task_objective or "",
            steps=plan.task_steps or [
                "Understand user requirements",
                "Select and verify appropriate tools",
                "Execute permitted actions safely",
                "Deliver verified outcome",
            ],
        )

        if not res.get("success"):
            msg = f"**Task Management Error:** {res.get('error')}"
        elif action == "create":
            t = res["task"]
            steps_str = "\n".join(f"  {idx+1}. {s}" for idx, s in enumerate(t['planned_steps']))
            msg = (
                f"**Task Tracking Record Initialized (Section 9 Compliance):**\n\n"
                f"• **Task ID:** `{t['task_id']}`\n"
                f"• **Objective:** {t['objective']}\n"
                f"• **Execution Status:** {t['execution_status']}\n"
                f"• **Next Immediate Action:** {t['next_immediate_action']}\n\n"
                f"**Planned Steps:**\n{steps_str}"
            )
        elif action == "list":
            tasks = res.get("tasks", [])
            if not tasks:
                msg = "No tasks currently registered in the task tracker."
            else:
                lines = [f"**Active Task Tracker ({len(tasks)} recorded tasks):**\n"]
                for t in tasks:
                    lines.append(f"• [`{t['task_id']}`] **{t['objective']}** — Status: *{t['execution_status']}*")
                msg = "\n".join(lines)
        else:
            t = res.get("task")
            if not t:
                msg = "No active task in memory."
            else:
                msg = (
                    f"**Current Task State:**\n\n"
                    f"• **Task ID:** `{t['task_id']}`\n"
                    f"• **Objective:** {t['objective']}\n"
                    f"• **Status:** {t['execution_status']}\n"
                    f"• **Next Action:** {t['next_immediate_action']}"
                )

        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(
            message=msg,
            state=self.state,
            action_taken="task_tracking",
            task_record=res.get("task"),
        )

    def _handle_general_query(self, user_input: str) -> AgentResult:
        """General Intelligence response adhering to 8-step operating principles."""
        help_msg = (
            "I am your Autonomous AI Agent, operating across all core domains:\n\n"
            "1. **General Intelligence & Reasoning:** Problem solving, analysis, and concept explanations.\n"
            "2. **Research & Web Intelligence:** Query web sources, compare evidence, and synthesize findings (`search web for <query>`).\n"
            "3. **Programming & Software Development:** Execute Python code and math evaluations (`run code: <script>` or `calculate <expression>`).\n"
            "4. **Business & Communications:** Draft and send emails via live Google SMTP or simulated dry-run (`send an email to <recipient>`).\n"
            "5. **Documents & Knowledge:** Read, write, search, and list workspace documents (`read file <path>`, `list files`).\n"
            "6. **Task Tracking & Automation:** Full Section 9 task state management (`create task: <goal>`, `list tasks`).\n\n"
            "How can I assist you today?"
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
                self.short_term_memory.active_context = {
                    "recipient_name": recipient_name,
                    "subject": subject,
                    "body": body,
                    "tone": tone,
                }
                ask_msg = (
                    f"Anti-Hallucination Guardrail: Could not find '{recipient_name}' in your contacts address book.\n"
                    f"To prevent dispatching to an incorrect address, please provide {recipient_name}'s email address (e.g., username@domain.com)."
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
                f"**Email Draft Prepared (Review & Confirmation Required)**\n\n"
                f"• **Recipient:** {draft.recipient_name} (`{draft.recipient_email}`)\n"
                f"• **Subject:** {draft.subject}\n"
                f"• **Tone:** {draft.tone.value if isinstance(draft.tone, ToneType) else draft.tone}\n\n"
                f"**Body Preview:**\n"
                f"```\n{draft.body}\n```\n\n"
                f"[SAFETY GUARDRAIL]: Sending an email is an irreversible action. "
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
            err_msg = f"[DISPATCH FAILED]: {smtp_res.get('error')}"
            self.short_term_memory.add_turn("assistant", err_msg)
            return AgentResult(message=err_msg, state=self.state, draft=draft)

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

        self.short_term_memory.record_sent(record)
        self.audit_log.record(record)
        self.state = AgentLifecycleState.IDLE

        success_msg = (
            f"**Email Sent Successfully:**\n\n"
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
        cancel_msg = "[ACTION CANCELLED]: The email draft has been discarded and no email was sent."
        self.short_term_memory.add_turn("assistant", cancel_msg)
        return AgentResult(message=cancel_msg, state=self.state, action_taken="draft_cancelled")

    def _handle_provided_missing_contact(self, user_input: str) -> AgentResult:
        """Processes user response providing the missing contact email."""
        found_emails = EMAIL_REGEX.findall(user_input)
        missing_name = self.short_term_memory.pending_missing_contact_name or "Contact"

        if not found_emails:
            retry_msg = (
                f"Could not detect a valid email address in '{user_input}'. "
                f"Please provide a valid email format for {missing_name} (e.g. name@domain.com) or type 'cancel'."
            )
            self.short_term_memory.add_turn("assistant", retry_msg)
            return AgentResult(message=retry_msg, state=self.state)

        email = found_emails[0].lower()
        self.add_contact_tool.run(
            name=missing_name,
            email=email,
            notes="Added dynamically during conversation flow",
        )

        ctx = self.short_term_memory.active_context or {}
        subject = ctx.get("subject", "Important Update")
        body = ctx.get("body", "Please see the following update.")
        tone = ctx.get("tone", "professional")

        self.short_term_memory.set_missing_contact_name(None)
        self.short_term_memory.active_context.clear()

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
            lines = ["**Contacts Address Book:**"]
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
            lines = ["**Recent Sent Emails Audit Log:**"]
            for r in reversed(recent):
                mode_tag = "[Dry-Run]" if r.is_dry_run else "[Live]"
                lines.append(f"• {mode_tag} **{r.sent_at[:19]}** to **{r.recipient_name}** (`{r.recipient_email}`)\n  Subject: *{r.subject}*")
            msg = "\n".join(lines)

        self.state = AgentLifecycleState.IDLE
        self.short_term_memory.add_turn("assistant", msg)
        return AgentResult(message=msg, state=self.state, action_taken="view_history")

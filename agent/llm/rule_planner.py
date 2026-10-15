"""Rule-based, deterministic NLP planner for offline operation and zero-dependency testing."""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, List
from agent.llm.base import BaseLLMClient, LLMPlan

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class RuleBasedPlanner(BaseLLMClient):
    """Deterministic reasoning engine that extracts entities, resolves context, and plans actions."""

    CONFIRM_PHRASES = {
        "yes", "y", "confirm", "send", "proceed", "send it", "approve",
        "looks good", "yes send it", "go ahead", "do it", "sure", "yep", "yeah", "ok", "okay"
    }

    REJECT_PHRASES = {
        "no", "n", "cancel", "stop", "abort", "don't send", "do not send",
        "reject", "hold on", "wait", "discard", "nevermind", "never mind"
    }

    REUSE_PATTERNS = [
        r"(?:send|forward)\s+(?:the\s+)?same(?:\s+email)?\s+to\s+([a-zA-Z0-9_\. ]+)",
        r"(?:send|email)\s+(?:this|it)\s+to\s+([a-zA-Z0-9_\. ]+)\s+(?:too|as well|also)",
        r"also\s+(?:send|email)\s+(?:to\s+)?([a-zA-Z0-9_\. ]+)",
        r"same\s+to\s+([a-zA-Z0-9_\. ]+)",
    ]

    TONE_KEYWORDS = {
        "urgent": ["urgent", "asap", "emergency", "immediately", "critical"],
        "casual": ["casual", "informal", "chill", "hey", "quick note"],
        "friendly": ["friendly", "warm", "kindly", "cheers"],
        "formal": ["formal", "official", "solemn", "respectfully"],
        "professional": ["professional", "work", "business", "meeting", "reminder", "submission"],
    }

    def plan(
        self,
        user_input: str,
        conversation_history: str = "",
        last_draft: Optional[Dict[str, Any]] = None,
        contacts_summary: str = "",
    ) -> LLMPlan:
        text = user_input.strip()
        lower = text.lower()

        # 1. Check for Confirmation
        if lower in self.CONFIRM_PHRASES or lower.rstrip(".!") in self.CONFIRM_PHRASES:
            return LLMPlan(
                intent="confirm_send",
                reasoning="User provided explicit affirmative confirmation to dispatch the pending draft."
            )

        # 2. Check for Rejection / Cancellation
        if lower in self.REJECT_PHRASES or lower.rstrip(".!") in self.REJECT_PHRASES:
            return LLMPlan(
                intent="reject_send",
                reasoning="User explicitly declined or cancelled the pending draft."
            )

        # 3. Check for Contact Query
        if any(k in lower for k in ["list contacts", "show contacts", "view contacts", "who is in my contacts", "address book"]):
            return LLMPlan(
                intent="list_contacts",
                reasoning="User requested to view the persistent contacts store."
            )

        # 4. Check for History Query
        if any(k in lower for k in ["sent emails", "view history", "show history", "what did i send", "sent messages", "audit log"]):
            return LLMPlan(
                intent="view_history",
                reasoning="User requested to view sent email records."
            )

        # 5. Check if user is replying with an email address
        found_emails = EMAIL_REGEX.findall(text)
        if found_emails and ("@" in text) and len(text.split()) <= 6:
            email = found_emails[0]
            words = [w for w in text.replace(email, "").strip().split() if w.lower() not in ("is", "it's", "email", ":", "=")]
            name = " ".join(words).strip() if words else email.split("@")[0].capitalize()
            return LLMPlan(
                intent="provide_contact",
                recipient_name=name,
                recipient_email=email,
                reasoning=f"User provided email address '{email}'."
            )

        # 6. Check for Task Tracking Operations (Section 9)
        if lower.startswith("create task:") or lower.startswith("new task:") or lower.startswith("add task:"):
            obj = text.split(":", 1)[1].strip()
            return LLMPlan(
                intent="task_ops",
                task_action="create",
                task_objective=obj,
                reasoning=f"Identified task creation request with objective '{obj}'."
            )
        if any(k in lower for k in ["list tasks", "show tasks", "get task", "task status", "view tasks"]):
            return LLMPlan(
                intent="task_ops",
                task_action="list" if "list" in lower or "show" in lower else "get",
                reasoning="User requested task tracking status."
            )

        # 7. Check for Code Execution & Calculator
        if lower.startswith("run code:") or lower.startswith("python:") or lower.startswith("exec:"):
            code_snippet = text.split(":", 1)[1].strip()
            return LLMPlan(
                intent="execute_code",
                code=code_snippet,
                reasoning="User explicitly commanded Python code execution."
            )
        if lower.startswith("calculate ") or lower.startswith("calc ") or lower.startswith("eval "):
            expr = re.sub(r"^(calculate|calc|eval)\s+", "", text, flags=re.IGNORECASE).strip()
            return LLMPlan(
                intent="execute_code",
                expression=expr,
                reasoning=f"Identified mathematical evaluation expression '{expr}'."
            )

        # 8. Check for Document Operations
        if lower.startswith("read file ") or lower.startswith("view file ") or lower.startswith("cat "):
            path = re.sub(r"^(read file|view file|cat)\s+", "", text, flags=re.IGNORECASE).strip()
            return LLMPlan(
                intent="document_ops",
                doc_action="read",
                doc_path=path,
                reasoning=f"Identified document read request for '{path}'."
            )
        if lower.startswith("write file ") or lower.startswith("write to file "):
            # Format: write file <path>: <content>
            parts = re.sub(r"^(write file|write to file)\s+", "", text, flags=re.IGNORECASE).split(":", 1)
            path = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else ""
            return LLMPlan(
                intent="document_ops",
                doc_action="write",
                doc_path=path,
                doc_content=content,
                reasoning=f"Identified document write request for '{path}'."
            )
        if lower in ["list files", "show files", "ls", "dir"]:
            return LLMPlan(
                intent="document_ops",
                doc_action="list",
                doc_path="",
                reasoning="Identified workspace file listing request."
            )
        if lower.startswith("search files for ") or lower.startswith("search docs for "):
            query = re.sub(r"^(search files for|search docs for)\s+", "", text, flags=re.IGNORECASE).strip()
            return LLMPlan(
                intent="document_ops",
                doc_action="search",
                query=query,
                reasoning=f"Identified document search query '{query}'."
            )

        # 9. Check for Web Research & Search
        if lower.startswith("search web for ") or lower.startswith("search web ") or lower.startswith("research ") or lower.startswith("web search:"):
            q = re.sub(r"^(search web for|search web|research|web search:)\s*", "", text, flags=re.IGNORECASE).strip()
            return LLMPlan(
                intent="web_search",
                query=q,
                reasoning=f"Identified web research query '{q}'."
            )

        # 10. Check for Context Reuse ("send the same email to Sarah too")
        for pat in self.REUSE_PATTERNS:
            match = re.search(pat, lower)
            if match:
                target_raw = match.group(1).strip()
                target_name = re.sub(r"\b(too|as well|also|please)\b", "", target_raw, flags=re.IGNORECASE).strip()
                if last_draft:
                    return LLMPlan(
                        intent="compose_email",
                        recipient_name=target_name.title(),
                        subject=last_draft.get("subject", "Follow up"),
                        body=last_draft.get("body", ""),
                        tone=last_draft.get("tone", "professional"),
                        reuse_context=True,
                        reasoning=f"Detected context reuse pattern targeting '{target_name}'. Reusing previous subject and body from memory."
                    )
                else:
                    return LLMPlan(
                        intent="compose_email",
                        recipient_name=target_name.title(),
                        reuse_context=True,
                        reasoning=f"User requested reuse for '{target_name}', but no prior draft is in memory."
                    )

        # 11. Check for Email Composition
        is_email_intent = any(keyword in lower for keyword in ["send an email", "send email", "email to", "send a mail", "write an email", "mail to", "message to"])

        if is_email_intent:
            recipient_name = self._extract_recipient_name(text)
            recipient_email = found_emails[0] if found_emails else None
            tone = self._detect_tone(text)
            subject = self._infer_subject(text, recipient_name)
            body = self._generate_body(text, recipient_name, subject, tone)

            return LLMPlan(
                intent="compose_email",
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                tone=tone,
                reuse_context=False,
                reasoning=f"Extracted email intent for recipient '{recipient_name}' with {tone} tone and subject '{subject}'."
            )

        # Default fallback: General conversation / reasoning
        return LLMPlan(
            intent="chat",
            reasoning="User entered general input; providing comprehensive assistance guidance."
        )

    def _extract_recipient_name(self, text: str) -> Optional[str]:
        lower = text.lower()
        if "dr. kunal meher" in lower or "dr kunal meher" in lower or "dr. kunal" in lower or "kunal meher" in lower or "prof meher" in lower:
            return "Dr. Kunal Meher"
        if "kunal" in lower and "meher" not in lower:
            return "Dr. Kunal Meher"
        if "john doe" in lower:
            return "John Doe"
        if "john" in lower:
            return "John Doe"
        if "sarah connor" in lower:
            return "Sarah Connor"
        if "sarah" in lower:
            return "Sarah Connor"
        if "alice smith" in lower or "alice" in lower:
            return "Alice Smith"

        # Regex extract: "to [Name] [about|reminding|regarding|asking]"
        match = re.search(r"(?:to|email|mail)\s+([A-Z][a-zA-Z\.\s]+?)(?:\s+(?:reminding|about|regarding|asking|stating|that|submitting|with)|\s*,|\s*$)", text)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in ("a", "an", "the", "him", "her", "them", "someone"):
                return candidate

        return None


    def _detect_tone(self, text: str) -> str:
        lower = text.lower()
        for tone, keywords in self.TONE_KEYWORDS.items():
            if any(k in lower for k in keywords):
                return tone
        return "professional"

    def _infer_subject(self, text: str, recipient_name: Optional[str]) -> str:
        lower = text.lower()
        match = re.search(r"(?:about|regarding|subject[:\s]+)\s+(.+?)(?:$|\.|\n)", text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            return raw[0].upper() + raw[1:]

        if "experiment 9" in lower:
            return "Submission: Experiment 9 AI Agent Assignment"
        if "assignment" in lower or "experiment" in lower:
            return "Submission: Autonomous AI Agent Assignment"

        if "meeting" in lower:
            return "Meeting Request and Schedule Confirmation"
        if "reminder" in lower:
            return "Gentle Reminder"
        if "update" in lower:
            return "Project Status and Updates"

        return "Important Communication"

    def _generate_body(self, text: str, recipient_name: Optional[str], subject: str, tone: str) -> str:
        salutation = f"Dear {recipient_name}," if recipient_name else "Hello,"
        signoff = "Best regards,\nVansh Jakhodia"

        lower = text.lower()
        if "experiment" in lower or "assignment" in lower:
            body_content = (
                f"I am writing to submit my completed assignment on the Autonomous AI Agent architecture.\n\n"
                f"The implementation includes multi-domain tool orchestration, deterministic reasoning, "
                f"short and long-term memory systems, safety guardrails, and verified execution capabilities.\n\n"
                f"Please let me know if you require any additional details or documentation."
            )
        elif "remind" in lower or "meeting" in lower:
            body_content = (
                f"I hope this message finds you well.\n\n"
                f"This is a brief follow-up regarding our upcoming schedule. "
                f"Please let me know if the proposed timing works or if we should make any adjustments."
            )
        else:
            body_content = (
                f"I hope you are doing well.\n\n"
                f"I am reaching out regarding {subject.lower()}.\n"
                f"Please review the information at your convenience and let me know your thoughts."
            )

        return f"{salutation}\n\n{body_content}\n\n{signoff}"

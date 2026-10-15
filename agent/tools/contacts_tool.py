"""Contact management tools with anti-hallucination guardrails."""

from __future__ import annotations
import re
from typing import Any, Dict, Optional
from agent.tools.base import BaseTool
from agent.memory.long_term import ContactsStore
from agent.models import Contact

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class ContactLookupTool(BaseTool):
    name = "lookup_contact"
    description = (
        "Looks up a person in the contacts address book by name, email, or alias. "
        "Strict anti-hallucination: returns found=False if contact is not registered."
    )

    def __init__(self, store: ContactsStore):
        self.store = store

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"found": False, "error": "Query cannot be empty"}

        contact: Optional[Contact] = self.store.search(query.strip())
        if contact:
            return {
                "found": True,
                "contact": contact.to_dict(),
                "message": f"Found contact {contact.name} with email {contact.email}",
            }

        return {
            "found": False,
            "query": query,
            "message": f"No contact found matching '{query}'. Must ask user for email address.",
        }


class ContactAddTool(BaseTool):
    name = "add_contact"
    description = "Adds or updates a verified contact in the persistent address book."

    def __init__(self, store: ContactsStore):
        self.store = store

    def run(self, name: str, email: str, role: Optional[str] = None, notes: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if not name or not name.strip():
            return {"success": False, "error": "Contact name is required"}
        if not email or not EMAIL_REGEX.match(email.strip()):
            return {"success": False, "error": f"Invalid email format: '{email}'"}

        contact = self.store.add_contact(
            name=name.strip(),
            email=email.strip().lower(),
            role=role.strip() if role else None,
            notes=notes.strip() if notes else None,
        )
        return {
            "success": True,
            "contact": contact.to_dict(),
            "message": f"Successfully registered contact {contact.name} ({contact.email})",
        }

"""Long-term memory: Persistent Contacts Store and Audit Log."""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from agent.models import Contact, SentRecord
from agent.config import config


class ContactsStore:
    """Persistent storage for address book with anti-hallucination guarantees."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or config.contacts_file
        self.contacts: Dict[str, Contact] = {}
        self._load()

    def _load(self) -> None:
        if not self.filepath.exists():
            # Seed default contacts
            self.contacts = {}
            self._seed_default_contacts()
            self._save()
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    contact = Contact.from_dict(item)
                    self.contacts[contact.id] = contact
        except Exception:
            self.contacts = {}
            self._seed_default_contacts()
            self._save()

    def _save(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self.contacts.values()], f, indent=2)

    def _seed_default_contacts(self) -> None:
        defaults = [
            Contact(
                name="Dr. Kunal Meher",
                email="kunal.meher@atlasuniversity.edu.in",
                aliases=["kunal", "dr kunal", "dr. kunal", "dr meher", "prof meher", "kunal meher"],
                role="Faculty / Professor",
                organization="Atlas SkillTech University",
                notes="Course Instructor for AI Agent Experiment 9"
            ),
            Contact(
                name="John Doe",
                email="john.doe@example.com",
                aliases=["john", "johnny"],
                role="Product Manager",
                organization="Acme Corp",
                notes="Project collaborator"
            ),
            Contact(
                name="Sarah Connor",
                email="sarah.connor@example.com",
                aliases=["sarah"],
                role="Engineering Lead",
                organization="Tech Innovations",
                notes="Team lead for software initiatives"
            ),
            Contact(
                name="Alice Smith",
                email="alice.smith@example.com",
                aliases=["alice"],
                role="UI/UX Designer",
                organization="Design Studio",
                notes="Lead designer"
            ),
        ]
        for c in defaults:
            self.contacts[c.id] = c

    def search(self, query: str) -> Optional[Contact]:
        """Search by email, name, or alias. Returns exact or best match."""
        q = query.strip().lower()
        if not q:
            return None

        # 1. Exact email match
        for contact in self.contacts.values():
            if contact.email.lower() == q:
                return contact

        # 2. Exact name match
        for contact in self.contacts.values():
            if contact.name.lower() == q:
                return contact

        # 3. Exact alias match
        for contact in self.contacts.values():
            for alias in contact.aliases:
                if alias.lower() == q:
                    return contact

        # 4. Fuzzy / Substring match (e.g. "kunal" in "Dr. Kunal Meher")
        for contact in self.contacts.values():
            if contact.matches(q):
                return contact

        # No match found - DO NOT HALLUCINATE
        return None

    def add_contact(self, name: str, email: str, role: Optional[str] = None, notes: Optional[str] = None) -> Contact:
        """Add or update a contact in the persistent store."""
        # Check if already exists by email
        existing = self.search(email)
        if existing:
            existing.name = name
            if role:
                existing.role = role
            if notes:
                existing.notes = notes
            self._save()
            return existing

        # Generate alias from first name
        first_name = name.split()[0].lower()
        aliases = [first_name]
        contact = Contact(name=name, email=email, aliases=aliases, role=role, notes=notes)
        self.contacts[contact.id] = contact
        self._save()
        return contact

    def list_all(self) -> List[Contact]:
        return list(self.contacts.values())


class AuditLog:
    """Persistent audit log of all email transactions and safety actions."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or config.audit_file
        self.records: List[SentRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.filepath.exists():
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.records = [
                    SentRecord(
                        record_id=d["record_id"],
                        draft_id=d["draft_id"],
                        recipient_name=d["recipient_name"],
                        recipient_email=d["recipient_email"],
                        subject=d["subject"],
                        body=d["body"],
                        sent_at=d["sent_at"],
                        status=d["status"],
                        is_dry_run=d.get("is_dry_run", False),
                        message_id=d.get("message_id"),
                        error=d.get("error"),
                    )
                    for d in data
                ]
        except Exception:
            self.records = []

    def _save(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.records], f, indent=2)

    def record(self, record: SentRecord) -> None:
        self.records.append(record)
        self._save()

    def get_recent(self, limit: int = 10) -> List[SentRecord]:
        return self.records[-limit:]

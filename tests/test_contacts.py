"""Unit tests for Contact Store and anti-hallucination lookup."""

import tempfile
from pathlib import Path
import pytest
from agent.memory.long_term import ContactsStore
from agent.tools.contacts_tool import ContactLookupTool, ContactAddTool


@pytest.fixture
def temp_contacts_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "contacts.json"
        store = ContactsStore(filepath=store_path)
        yield store


def test_seed_contacts_contain_dr_kunal_meher(temp_contacts_store):
    """Verify Dr. Kunal Meher is registered with official university email."""
    contact = temp_contacts_store.search("Dr. Kunal Meher")
    assert contact is not None
    assert contact.email == "kunal.meher@atlasuniversity.edu.in"
    assert "kunal" in contact.aliases


def test_alias_lookup(temp_contacts_store):
    """Verify alias and fuzzy matching work."""
    c1 = temp_contacts_store.search("kunal")
    assert c1 is not None
    assert c1.email == "kunal.meher@atlasuniversity.edu.in"

    c2 = temp_contacts_store.search("john")
    assert c2 is not None
    assert c2.email == "john.doe@example.com"


def test_anti_hallucination_for_unknown_contact(temp_contacts_store):
    """Verify contact lookup returns found=False for unknown contacts."""
    lookup_tool = ContactLookupTool(temp_contacts_store)
    result = lookup_tool.run(query="UnknownPerson")
    assert result["found"] is False
    assert "No contact found" in result["message"]


def test_add_new_contact(temp_contacts_store):
    """Verify dynamic contact addition and persistence."""
    add_tool = ContactAddTool(temp_contacts_store)
    res = add_tool.run(name="Robert Downey", email="rdj@example.com", role="Actor")
    assert res["success"] is True

    # Now lookup should succeed
    found = temp_contacts_store.search("Robert Downey")
    assert found is not None
    assert found.email == "rdj@example.com"

"""FastAPI Web Server for Autonomous AI Agent.

Assignment: Experiment 9 - Autonomous AI Agent
Production architecture: Serves clean responsive interface from templates/index.html.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.orchestrator import AIAgent

app = FastAPI(title="Autonomous AI Agent", version="2.1.0")
agent = AIAgent()
TEMPLATE_FILE = Path(__file__).resolve().parent / "templates" / "index.html"


class ChatRequest(BaseModel):
    message: str


class AddContactRequest(BaseModel):
    name: str
    email: str
    role: Optional[str] = None


class ActionRequest(BaseModel):
    action: str  # "confirm" or "cancel"


@app.get("/api/state")
def get_state():
    last_draft = agent.short_term_memory.get_last_draft()
    pending_draft = agent.short_term_memory.pending_draft
    return {
        "state": agent.state.value,
        "turns_count": len(agent.short_term_memory.turns),
        "has_pending_draft": pending_draft is not None,
        "pending_draft": pending_draft.to_dict() if pending_draft else None,
        "last_draft": last_draft.to_dict() if last_draft else None,
        "config": {
            "smtp_user": agent.config.smtp_user,
            "smtp_host": agent.config.smtp_host,
            "dry_run": agent.config.dry_run,
            "sender_name": agent.config.sender_name,
            "llm_provider": agent.config.llm_provider,
        },
    }


@app.get("/api/contacts")
def list_contacts():
    return [c.to_dict() for c in agent.contacts_store.list_all()]


@app.post("/api/contacts")
def add_contact(req: AddContactRequest):
    res = agent.add_contact_tool.run(name=req.name, email=req.email, role=req.role)
    return res


@app.get("/api/history")
def list_history():
    return [r.to_dict() for r in reversed(agent.audit_log.get_recent(20))]


@app.post("/api/chat")
def chat(req: ChatRequest):
    result = agent.process(req.message)
    return {
        "message": result.message,
        "state": result.state.value,
        "action_taken": result.action_taken,
        "requires_confirmation": result.requires_confirmation,
        "draft": result.draft.to_dict() if result.draft else None,
        "sent_record": result.sent_record.to_dict() if result.sent_record else None,
    }


@app.post("/api/action")
def take_action(req: ActionRequest):
    if req.action.lower() in ("confirm", "send", "yes"):
        result = agent.process("yes")
    else:
        result = agent.process("no")

    return {
        "message": result.message,
        "state": result.state.value,
        "action_taken": result.action_taken,
        "draft": result.draft.to_dict() if result.draft else None,
        "sent_record": result.sent_record.to_dict() if result.sent_record else None,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    if TEMPLATE_FILE.exists():
        content = TEMPLATE_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Template index.html not found</h1>", status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

"""FastAPI Web Server for Autonomous AI Agent.

Full multi-domain architecture:
- General Intelligence
- Code Execution & Calculator
- Web Research & Citations
- Documents & File Knowledge
- Task Tracking (Section 9 Compliance)
- Business Communications & Google SMTP Delivery
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.orchestrator import AIAgent

app = FastAPI(title="Autonomous AI Agent", version="2.2.0")
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


class CreateTaskRequest(BaseModel):
    objective: str
    steps: Optional[List[str]] = None


@app.get("/api/state")
def get_state():
    last_draft = agent.short_term_memory.get_last_draft()
    pending_draft = agent.short_term_memory.pending_draft
    tasks_res = agent.task_tool.run(action="list")
    return {
        "state": agent.state.value,
        "turns_count": len(agent.short_term_memory.turns),
        "has_pending_draft": pending_draft is not None,
        "pending_draft": pending_draft.to_dict() if pending_draft else None,
        "last_draft": last_draft.to_dict() if last_draft else None,
        "tasks_count": tasks_res.get("count", 0),
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


@app.get("/api/tasks")
def list_tasks():
    return agent.task_tool.run(action="list")


@app.post("/api/tasks")
def create_task(req: CreateTaskRequest):
    return agent.task_tool.run(action="create", objective=req.objective, steps=req.steps)


@app.get("/api/tools")
def list_tools():
    return {
        "code_executor": agent.code_tool.description,
        "web_search": agent.web_tool.description,
        "document_manager": agent.doc_tool.description,
        "task_tracker": agent.task_tool.description,
        "contact_lookup": agent.lookup_tool.description,
        "contact_add": agent.add_contact_tool.description,
        "draft_email": agent.draft_tool.description,
        "safety_guardrail": agent.guardrail_tool.description,
        "smtp_sender": agent.smtp_tool.description,
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    result = agent.process(req.message)
    return result.to_dict()


@app.post("/api/action")
def take_action(req: ActionRequest):
    if req.action.lower() in ("confirm", "send", "yes"):
        result = agent.process("yes")
    else:
        result = agent.process("no")
    return result.to_dict()


@app.get("/", response_class=HTMLResponse)
def index():
    if TEMPLATE_FILE.exists():
        content = TEMPLATE_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Template index.html not found</h1>", status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

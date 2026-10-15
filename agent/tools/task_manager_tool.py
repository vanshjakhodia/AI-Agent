"""Task tracking and record-keeping tool adhering to Section 9 of the Master Prompt."""

from __future__ import annotations
import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.tools.base import BaseTool


class TaskStatus(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    WAITING_FOR_APPROVAL = "Waiting for Approval"
    COMPLETED = "Completed"
    FAILED = "Failed"


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    objective: str
    requirements_and_constraints: List[str] = Field(default_factory=list)
    planned_steps: List[str] = Field(default_factory=list)
    execution_status: TaskStatus = TaskStatus.NOT_STARTED
    completed_subtasks: List[str] = Field(default_factory=list)
    unresolved_blockers: List[str] = Field(default_factory=list)
    next_immediate_action: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "requirements_and_constraints": self.requirements_and_constraints,
            "planned_steps": self.planned_steps,
            "execution_status": self.execution_status.value,
            "completed_subtasks": self.completed_subtasks,
            "unresolved_blockers": self.unresolved_blockers,
            "next_immediate_action": self.next_immediate_action,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskManagerTool(BaseTool):
    """Maintains task state, plan steps, and completion records per Section 9."""

    name: str = "task_tracker"
    description: str = (
        "Maintains structured task records: Objective, Requirements & Constraints, "
        "Planned Steps, Execution Status, Completed Subtasks, Blockers, and Next Action."
    )

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}

    def run(
        self,
        action: str = "get",
        task_id: Optional[str] = None,
        objective: str = "",
        requirements: Optional[List[str]] = None,
        steps: Optional[List[str]] = None,
        status: Optional[str] = None,
        completed_step: Optional[str] = None,
        blocker: Optional[str] = None,
        next_action: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Manage task records."""
        action_clean = action.lower().strip()

        if action_clean == "create":
            if not objective:
                return {"success": False, "error": "Objective is required to create a task."}
            task = TaskRecord(
                objective=objective,
                requirements_and_constraints=requirements or [],
                planned_steps=steps or [],
                execution_status=TaskStatus.IN_PROGRESS,
                next_immediate_action=next_action or (steps[0] if steps else "Begin execution"),
            )
            self._tasks[task.task_id] = task
            return {
                "success": True,
                "action": "create",
                "task": task.to_dict(),
            }

        elif action_clean == "update":
            if not task_id or task_id not in self._tasks:
                return {"success": False, "error": f"Task '{task_id}' not found."}
            task = self._tasks[task_id]

            if status:
                try:
                    task.execution_status = TaskStatus(status)
                except ValueError:
                    task.execution_status = TaskStatus[status.upper().replace(" ", "_")]

            if completed_step and completed_step not in task.completed_subtasks:
                task.completed_subtasks.append(completed_step)

            if blocker and blocker not in task.unresolved_blockers:
                task.unresolved_blockers.append(blocker)

            if next_action:
                task.next_immediate_action = next_action

            task.updated_at = time.time()
            return {"success": True, "action": "update", "task": task.to_dict()}

        elif action_clean == "get":
            if task_id:
                if task_id in self._tasks:
                    return {"success": True, "task": self._tasks[task_id].to_dict()}
                return {"success": False, "error": f"Task '{task_id}' not found."}
            # Return active or last task
            if self._tasks:
                last_task = list(self._tasks.values())[-1]
                return {"success": True, "task": last_task.to_dict()}
            return {"success": True, "task": None, "message": "No active tasks recorded."}

        elif action_clean == "list":
            return {
                "success": True,
                "tasks": [t.to_dict() for t in self._tasks.values()],
                "count": len(self._tasks),
            }

        return {"success": False, "error": f"Unknown action '{action}'. Use create, update, get, or list."}

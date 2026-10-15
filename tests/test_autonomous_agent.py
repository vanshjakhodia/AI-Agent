"""Comprehensive test suite for Autonomous AI Agent multi-domain capabilities.

Validates:
- Code Execution & Calculator
- Web Research & Citations
- Document Knowledge & Security Isolation
- Section 9 Task Tracking & State Transitions
- Multi-domain Orchestration via AIAgent
"""

from pathlib import Path
import pytest
from agent.orchestrator import AIAgent
from agent.tools.code_exec_tool import CodeExecutionTool
from agent.tools.web_search_tool import WebSearchTool
from agent.tools.document_tool import DocumentTool
from agent.tools.task_manager_tool import TaskManagerTool, TaskStatus
from agent.models import AgentLifecycleState


def test_code_execution_math_expression():
    tool = CodeExecutionTool()
    res = tool.run(expression="25 * 40 + math.sqrt(144)")
    assert res["success"] is True
    assert res["result"] == 1012.0
    assert "1012" in res["stdout"]


def test_code_execution_python_script():
    tool = CodeExecutionTool()
    code = "import sys\nprint('Autonomous AI Agent active')\nprint(f'Sum: {sum([1,2,3,4,5])}')"
    res = tool.run(code=code)
    assert res["success"] is True
    assert res["exit_code"] == 0
    assert "Autonomous AI Agent active" in res["stdout"]
    assert "Sum: 15" in res["stdout"]


def test_code_execution_error_handling():
    tool = CodeExecutionTool()
    res = tool.run(code="raise ValueError('Intentional verification error')")
    assert res["success"] is False
    assert res["exit_code"] != 0
    assert "ValueError" in res["stderr"]


def test_web_search_tool():
    tool = WebSearchTool()
    res = tool.run(query="Autonomous AI Agent architecture")
    assert res["success"] is True
    assert res["count"] > 0
    assert len(res["results"]) > 0
    first = res["results"][0]
    assert "title" in first
    assert "url" in first
    assert "snippet" in first


def test_document_tool_lifecycle(tmp_path):
    doc_tool = DocumentTool(base_dir=str(tmp_path))

    # 1. Write file
    w_res = doc_tool.run(action="write", file_path="notes.txt", content="Testing Autonomous Agent knowledge system.")
    assert w_res["success"] is True
    assert w_res["bytes_written"] > 0

    # 2. Read file
    r_res = doc_tool.run(action="read", file_path="notes.txt")
    assert r_res["success"] is True
    assert "Testing Autonomous Agent" in r_res["content"]

    # 3. List files
    l_res = doc_tool.run(action="list")
    assert l_res["success"] is True
    assert any(item["name"] == "notes.txt" for item in l_res["items"])

    # 4. Search files
    s_res = doc_tool.run(action="search", query="Autonomous")
    assert s_res["success"] is True
    assert s_res["count"] >= 1
    assert any(m["file"] == "notes.txt" for m in s_res["matches"])


def test_document_tool_security_isolation(tmp_path):
    doc_tool = DocumentTool(base_dir=str(tmp_path))

    # 1. Path traversal outside root must be blocked
    res = doc_tool.run(action="read", file_path="../../etc/passwd")
    assert res["success"] is False
    assert "Access denied" in res["error"]

    # 2. Secret / .env files must be blocked
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=12345")
    res_env = doc_tool.run(action="read", file_path=".env")
    assert res_env["success"] is False
    assert "Security Policy" in res_env["error"]


def test_task_manager_section_9_compliance():
    task_tool = TaskManagerTool()

    # 1. Create Task
    create_res = task_tool.run(
        action="create",
        objective="Deploy autonomous AI Agent multi-agent system",
        requirements=["Zero emojis", "Safe tool execution", "MIT License"],
        steps=["Design architecture", "Implement tools", "Pass test suite", "Push to GitHub"],
        next_action="Design architecture",
    )
    assert create_res["success"] is True
    task_id = create_res["task"]["task_id"]
    assert create_res["task"]["execution_status"] == TaskStatus.IN_PROGRESS.value

    # 2. Update step completion
    up_res = task_tool.run(
        action="update",
        task_id=task_id,
        completed_step="Design architecture",
        next_action="Implement tools",
    )
    assert up_res["success"] is True
    assert "Design architecture" in up_res["task"]["completed_subtasks"]
    assert up_res["task"]["next_immediate_action"] == "Implement tools"

    # 3. Get task state
    get_res = task_tool.run(action="get", task_id=task_id)
    assert get_res["success"] is True
    assert get_res["task"]["task_id"] == task_id


def test_orchestrator_multi_domain_execution():
    agent = AIAgent()

    # Domain 1: Math evaluation
    r1 = agent.process("calculate 125 * 8")
    assert r1.action_taken == "code_execution"
    assert "1000" in r1.message

    # Domain 2: Python Code Runner
    r2 = agent.process("run code: print('Hello Autonomous Agent')")
    assert r2.action_taken == "code_execution"
    assert "Hello Autonomous Agent" in r2.message

    # Domain 3: Task Manager (Section 9)
    r3 = agent.process("create task: Build production autonomous agent")
    assert r3.action_taken == "task_tracking"
    assert "Task Tracking Record Initialized" in r3.message

    # Domain 4: Web Research
    r4 = agent.process("search web for Autonomous Agent architectures")
    assert r4.action_taken == "web_search"
    assert "Research Results for" in r4.message

    # Domain 5: Document Listing
    r5 = agent.process("list files")
    assert r5.action_taken == "document_operation"
    assert "Workspace Directory" in r5.message

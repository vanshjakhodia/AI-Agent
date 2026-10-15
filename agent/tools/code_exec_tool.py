"""Code execution and evaluation tool for the AI Agent."""

from __future__ import annotations
import io
import sys
import time
import traceback
import subprocess
from typing import Any, Dict
from agent.tools.base import BaseTool


class CodeExecutionTool(BaseTool):
    """Executes Python code or calculations safely and returns stdout/stderr/results."""

    name: str = "code_executor"
    description: str = (
        "Executes Python code snippets, mathematical evaluations, and data transformations. "
        "Captures output, errors, and returned values."
    )

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def run(self, code: str = "", expression: str = "", **kwargs) -> Dict[str, Any]:
        """Execute Python code or evaluate an expression."""
        if not code and not expression:
            return {
                "success": False,
                "error": "No code or expression provided for execution.",
                "stdout": "",
                "stderr": "",
            }

        start_time = time.time()

        # If expression is provided, evaluate it
        if expression:
            try:
                # Safe evaluation with restricted builtins
                safe_builtins = {
                    "abs": abs, "round": round, "min": min, "max": max,
                    "sum": sum, "len": len, "pow": pow, "range": range,
                    "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
                    "list": list, "dict": dict, "set": set, "tuple": tuple,
                    "str": str, "int": int, "float": float, "bool": bool
                }
                import math
                eval_locals = {"math": math}
                result = eval(expression, {"__builtins__": safe_builtins}, eval_locals)
                duration = round(time.time() - start_time, 4)
                return {
                    "success": True,
                    "expression": expression,
                    "result": result,
                    "stdout": str(result),
                    "stderr": "",
                    "duration_seconds": duration,
                }
            except Exception as e:
                return {
                    "success": False,
                    "expression": expression,
                    "error": str(e),
                    "stdout": "",
                    "stderr": traceback.format_exc(),
                }

        # Otherwise execute code in isolated subprocess for safety
        try:
            process = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            duration = round(time.time() - start_time, 4)
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "duration_seconds": duration,
                "code": code,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {self.timeout} seconds.",
                "stdout": "",
                "stderr": "TimeoutExpired",
                "duration_seconds": self.timeout,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": traceback.format_exc(),
            }

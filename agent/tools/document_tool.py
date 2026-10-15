"""Document and file knowledge tool for the AI Agent."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List
from agent.tools.base import BaseTool


class DocumentTool(BaseTool):
    """Reads, writes, searches, and summarizes workspace documents and files."""

    name: str = "document_manager"
    description: str = (
        "Reads, writes, lists, and searches local files and documents. "
        "Allows analyzing content, extracting knowledge, and managing workspace data."
    )

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).resolve()

    def _safe_path(self, relative_path: str) -> Path:
        """Ensure file path stays within the permitted workspace directory."""
        target = (self.base_dir / relative_path).resolve()
        # Security: protect against path traversal outside project root
        if not str(target).startswith(str(self.base_dir)):
            raise PermissionError(f"Access denied: Path '{relative_path}' is outside the authorized workspace.")
        return target

    def run(self, action: str = "read", file_path: str = "", content: str = "", query: str = "", **kwargs) -> Dict[str, Any]:
        """Execute document action: read, write, list, search, or summarize."""
        action_clean = action.lower().strip()

        try:
            if action_clean == "read":
                if not file_path:
                    return {"success": False, "error": "file_path is required for read action."}
                target = self._safe_path(file_path)
                if not target.exists():
                    return {"success": False, "error": f"File '{file_path}' does not exist."}
                if target.is_dir():
                    return {"success": False, "error": f"Path '{file_path}' is a directory, use action='list'."}
                
                # Check for sensitive files (e.g. .env) per Section 7
                if target.name == ".env" or "key" in target.name.lower() or "secret" in target.name.lower():
                    return {
                        "success": False,
                        "error": "Access blocked by Security Policy: Credentials and secret files cannot be accessed directly."
                    }

                text = target.read_text(encoding="utf-8", errors="replace")
                return {
                    "success": True,
                    "action": "read",
                    "file_path": str(file_path),
                    "size_bytes": len(text),
                    "lines_count": len(text.splitlines()),
                    "content": text,
                }

            elif action_clean == "write":
                if not file_path:
                    return {"success": False, "error": "file_path is required for write action."}
                target = self._safe_path(file_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return {
                    "success": True,
                    "action": "write",
                    "file_path": str(file_path),
                    "bytes_written": len(content),
                }

            elif action_clean == "list":
                dir_path = self._safe_path(file_path) if file_path else self.base_dir
                if not dir_path.exists():
                    return {"success": False, "error": f"Directory '{file_path}' does not exist."}
                
                items: List[Dict[str, Any]] = []
                for entry in sorted(os.listdir(dir_path)):
                    if entry.startswith(".") or entry == "__pycache__":
                        continue
                    full = dir_path / entry
                    items.append({
                        "name": entry,
                        "is_dir": full.is_dir(),
                        "size": full.stat().st_size if full.is_file() else None,
                    })
                return {
                    "success": True,
                    "action": "list",
                    "directory": str(file_path or "."),
                    "items": items,
                    "count": len(items),
                }

            elif action_clean == "search":
                if not query:
                    return {"success": False, "error": "query is required for search action."}
                matches: List[Dict[str, Any]] = []
                for root, dirs, files in os.walk(self.base_dir):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
                    for f in files:
                        if f.startswith(".") or f.endswith((".pyc", ".png", ".jpg", ".zip")):
                            continue
                        p = Path(root) / f
                        try:
                            c = p.read_text(encoding="utf-8", errors="ignore")
                            if query.lower() in c.lower():
                                rel = p.relative_to(self.base_dir)
                                matches.append({
                                    "file": str(rel),
                                    "occurrences": c.lower().count(query.lower()),
                                })
                        except Exception:
                            continue
                return {
                    "success": True,
                    "action": "search",
                    "query": query,
                    "matches": matches,
                    "count": len(matches),
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action '{action}'. Supported actions: read, write, list, search.",
                }

        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

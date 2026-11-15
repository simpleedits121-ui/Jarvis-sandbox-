from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any


class SwarmStore:
    """Small JSON-backed store. Writes are atomic and confined to its own directory."""

    def __init__(self, workspace: Path):
        self.root = (workspace / "swarm").resolve()
        self.tasks_dir = self.root / "tasks"
        self.memory_dir = self.root / "memory"
        self.messages_dir = self.root / "messages"
        for directory in (self.tasks_dir, self.memory_dir, self.messages_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _write(self, path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)

    def _read(self, path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    def save_task(self, task: dict[str, Any]) -> None:
        with self._lock:
            self._write(self.tasks_dir / f"{task['task_id']}.json", task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        if not task_id or Path(task_id).name != task_id:
            return None
        return self._read(self.tasks_dir / f"{task_id}.json")

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = [row for path in self.tasks_dir.glob("*.json") if (row := self._read(path))]
        rows.sort(key=lambda row: row.get("created_at", 0), reverse=True)
        return rows[:max(1, min(limit, 100))]

    def save_memory(self, agent_id: str, entry: dict[str, Any]) -> None:
        if Path(agent_id).name != agent_id:
            raise ValueError("Invalid agent id")
        path = self.memory_dir / f"{agent_id}.json"
        with self._lock:
            current = self._read(path) or {"agent_id": agent_id, "entries": []}
            entries = current.get("entries", [])
            if not isinstance(entries, list):
                entries = []
            entries.append(entry)
            current["entries"] = entries[-100:]
            self._write(path, current)

    def get_memory(self, agent_id: str) -> dict[str, Any]:
        if Path(agent_id).name != agent_id:
            return {"agent_id": agent_id, "entries": []}
        return self._read(self.memory_dir / f"{agent_id}.json") or {"agent_id": agent_id, "entries": []}

    def add_message(self, task_id: str, sender: str, recipient: str, content: str) -> dict[str, Any]:
        if Path(task_id).name != task_id:
            raise ValueError("Invalid task id")
        path = self.messages_dir / f"{task_id}.json"
        with self._lock:
            current = self._read(path) or {"task_id": task_id, "messages": []}
            message = {"message_id": str(uuid.uuid4()), "sender": sender,
                       "recipient": recipient, "content": content[:4000]}
            messages = current.get("messages", [])
            if not isinstance(messages, list):
                messages = []
            messages.append(message)
            current["messages"] = messages[-200:]
            self._write(path, current)
            return message

    def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        if Path(task_id).name != task_id:
            return []
        value = self._read(self.messages_dir / f"{task_id}.json") or {}
        messages = value.get("messages", [])
        return messages if isinstance(messages, list) else []

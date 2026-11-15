from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .registry import AGENTS, get_agent, public_agents
from .store import SwarmStore


class SwarmRuntime:
    """Offline coordination runtime; it does not claim neural reasoning or Blender control."""

    def __init__(self, workspace: Path):
        self.store = SwarmStore(workspace)

    def agents(self) -> list[dict[str, object]]:
        return public_agents()

    def create_task(self, goal: str) -> dict[str, Any]:
        goal = goal.strip()
        if not 3 <= len(goal) <= 4000:
            raise ValueError("Task must contain 3 to 4000 characters")
        task_id = str(uuid.uuid4())
        lower = goal.lower()
        assigned = ["design", "geometry", "appearance", "supervisor", "quality"]
        if any(word in lower for word in ("reference", "image", "photo", "picture")):
            assigned.insert(0, "vision")
        if any(word in lower for word in ("rig", "skeleton", "animation", "deform")):
            assigned.insert(-2, "rigging")
        subtasks = []
        for agent_id in assigned:
            agent = get_agent(agent_id)
            subtasks.append({"subtask_id": str(uuid.uuid4()), "agent_id": agent_id,
                             "agent_name": agent.name if agent else agent_id,
                             "objective": agent.objective if agent else "Complete assigned work",
                             "status": "pending", "result": None})
        task = {"task_id": task_id, "goal": goal, "status": "queued",
                "execution_mode": "offline_coordination", "reasoning_available": False,
                "created_at": int(time.time()), "updated_at": int(time.time()),
                "subtasks": subtasks, "review": None}
        self.store.save_task(task)
        self.store.add_message(task_id, "orchestrator", "team", f"New task received: {goal}")
        return task

    def run_task(self, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id)
        if not task:
            raise KeyError("Task not found")
        if task.get("status") == "completed":
            return task
        task["status"] = "running"
        task["updated_at"] = int(time.time())
        self.store.save_task(task)
        for subtask in task.get("subtasks", []):
            agent_id = subtask.get("agent_id", "")
            agent = get_agent(agent_id)
            if not agent:
                subtask["status"] = "blocked"
                subtask["result"] = "Unknown agent"
                continue
            subtask["status"] = "running"
            self.store.save_task(task)
            result = self._offline_work(agent_id, task["goal"], task)
            subtask["result"] = result
            subtask["status"] = "completed"
            self.store.save_memory(agent_id, {"task_id": task_id, "at": int(time.time()),
                                              "goal": task["goal"][:500], "result_summary": result[:700]})
            self.store.add_message(task_id, agent_id, "orchestrator", result)
            task["updated_at"] = int(time.time())
            self.store.save_task(task)
        completed = all(item.get("status") == "completed" for item in task.get("subtasks", []))
        task["status"] = "review" if completed else "blocked"
        task["review"] = {
            "agent_id": "supervisor",
            "status": "needs_local_model_review",
            "note": "Offline coordination completed. A local reasoning model and Blender scene telemetry are required for substantive visual inspection and corrective geometry work.",
        }
        task["updated_at"] = int(time.time())
        self.store.save_task(task)
        return task

    def _offline_work(self, agent_id: str, goal: str, task: dict[str, Any]) -> str:
        agent = get_agent(agent_id)
        if agent_id == "supervisor":
            done = [item["agent_id"] for item in task.get("subtasks", []) if item.get("status") == "completed"]
            return "Coordination check: completed agent reports from " + ", ".join(done) + ". Visual quality is not verified because no Blender telemetry or local vision model is connected."
        if agent_id == "quality":
            return "Acceptance checklist prepared: reference fidelity, anatomy, topology, materials, UVs, rigging/deformation, multi-angle consistency and export validation. No item is marked visually passed without evidence."
        if agent_id == "vision":
            return "Reference-analysis task registered. Offline mode cannot infer image contents yet; provide reference images to the future local vision pipeline. Record front, side, back and detail views when available."
        if agent_id == "design":
            return f"Design brief prepared for: {goal}. Define silhouette, proportions, face, hair, clothing, palette and reference-specific details before geometry approval."
        if agent_id == "geometry":
            return "Geometry work plan prepared: establish proportion blockout, connected primary forms, clean topology, hands/face detail, clothing thickness and multi-angle checks. No mesh was generated by this coordination step."
        if agent_id == "appearance":
            return "Appearance plan prepared: define material palette, UV strategy, skin/eye/hair shaders, clothing materials, texture resolution and seam checks. No textures were generated by this coordination step."
        if agent_id == "rigging":
            return "Rigging plan prepared: define skeleton hierarchy, deformation zones, weight-paint checks, facial controls and pose tests. No rig was generated by this coordination step."
        return f"{agent.name if agent else agent_id} received the task and recorded an offline work plan."

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.store.get_task(task_id)

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list_tasks(limit)

    def messages(self, task_id: str) -> list[dict[str, Any]]:
        return self.store.list_messages(task_id)

    def memory(self, agent_id: str) -> dict[str, Any]:
        if not get_agent(agent_id):
            raise KeyError("Agent not found")
        return self.store.get_memory(agent_id)

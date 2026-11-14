from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from .workers import build_scene_project

SYSTEM_PROMPT = """You are JARVIS, the director of a CPU-first Android production worker swarm.
You do not pretend to control Android apps unless a registered tool does so. You can delegate safe tasks to local workers.
Available tools:
- list_workspace: no arguments; list files and folders in the JARVIS worker workspace.
- read_text_file: {\"name\":\"relative/path\"}; read a small text file in the workspace.
- create_text_file: {\"name\":\"file.txt\",\"content\":\"...\"}; create a NEW text file. Existing files require user approval to overwrite.
- create_blender_scene: {\"name\":\"anime_lab\",\"description\":\"...\"}; delegates to Geometry, Material, World, Camera, Animation and Quality workers. It creates a Blender Python build script and OBJ/MTL preview using CPU procedural geometry.
- delete_file: {\"name\":\"relative/path\"}; always asks user approval before deletion.
- run_blender_project: {\"name\":\"project-folder\"}; always asks user approval. Only works if a Blender executable is available to the Termux worker.
Return ONLY a JSON object: {\"reply\":\"short natural language response\",\"actions\":[{\"tool\":\"tool_name\",\"arguments\":{}}]}.
Use an empty actions array when no tool is needed. Never return shell commands, Python code, arbitrary scripts, URLs to download, or tools not listed above. Never request destructive action without explaining why. For a scene request, call create_blender_scene. For a request involving a person's photo, explain that the current procedural scene worker only creates a placeholder and does not reconstruct identity from the photo yet.
"""

class AgentConfigRequest(BaseModel):
    local_base_url: str = Field(default="http://127.0.0.1:8080/v1", max_length=300)
    local_model: str = Field(default="", max_length=200)
    remote_base_url: str = Field(default="https://api.openai.com/v1", max_length=300)
    remote_model: str = Field(default="gpt-4o-mini", max_length=200)
    remote_api_key: str | None = Field(default=None, max_length=500)
    clear_remote_key: bool = False

class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)

class ApprovalRequest(BaseModel):
    approved: bool


CONFIG_ROOT = Path(os.environ.get("JARVIS_CONFIG_HOME", Path.home() / ".config" / "jarvis-sandbox")).resolve()


def config_path(root: Path) -> Path:
    # Keep provider credentials in Termux private home, never in shared Downloads.
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    return CONFIG_ROOT / "agent-settings.json"


def load_config(root: Path) -> dict[str, str]:
    defaults = {
        "local_base_url": os.environ.get("JARVIS_LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
        "local_model": os.environ.get("JARVIS_LOCAL_LLM_MODEL", ""),
        "remote_base_url": os.environ.get("JARVIS_REMOTE_LLM_BASE_URL", "https://api.openai.com/v1"),
        "remote_model": os.environ.get("JARVIS_REMOTE_LLM_MODEL", "gpt-4o-mini"),
        "remote_api_key": os.environ.get("JARVIS_REMOTE_LLM_API_KEY", ""),
    }
    try:
        saved = json.loads(config_path(root).read_text(encoding="utf-8"))
        for key in defaults:
            if key in saved:
                defaults[key] = str(saved[key])
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def save_config(root: Path, config: dict[str, str]) -> None:
    path = config_path(root)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def public_config(config: dict[str, str]) -> dict[str, Any]:
    return {
        "local_base_url": config["local_base_url"],
        "local_model": config["local_model"],
        "remote_base_url": config["remote_base_url"],
        "remote_model": config["remote_model"],
        "local_configured": bool(config["local_base_url"] and config["local_model"]),
        "remote_configured": bool(config["remote_base_url"] and config["remote_model"] and config["remote_api_key"]),
        "remote_key_set": bool(config["remote_api_key"]),
        "strategy": "local-first, remote fallback",
    }


def _chat_url(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


async def call_model(base: str, model: str, api_key: str, messages: list[dict[str, str]]) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    async with httpx.AsyncClient(timeout=httpx.Timeout(75.0, connect=8.0)) as client:
        response = await client.post(_chat_url(base), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data["choices"][0]["message"].get("content") or "")


def parse_plan(content: str) -> dict[str, Any]:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"reply": content[:4000], "actions": []}


def safe_workspace_path(root: Path, name: str) -> Path:
    if Path(name).name == "agent-settings.json":
        raise HTTPException(403, "Private agent credentials are not available to AI tools.")
    candidate = (root / name).resolve()
    if candidate != root.resolve() and root.resolve() not in candidate.parents:
        raise HTTPException(400, "Path escapes the JARVIS workspace.")
    if candidate == root.resolve():
        raise HTTPException(400, "Workspace root is not a file.")
    return candidate


def pending_dir(root: Path) -> Path:
    p = root / "approvals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def queue_approval(root: Path, action: str, arguments: dict[str, Any], reason: str) -> dict[str, Any]:
    approval_id = str(uuid.uuid4())
    row = {"approval_id": approval_id, "action": action, "arguments": arguments,
           "reason": reason, "status": "pending", "created_at": int(time.time())}
    (pending_dir(root) / f"{approval_id}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def list_approvals(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in pending_dir(root).glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if row.get("status") == "pending":
                rows.append(row)
        except Exception:
            continue
    return sorted(rows, key=lambda x: x.get("created_at", 0), reverse=True)


def run_approved_action(root: Path, action: str, args: dict[str, Any]) -> dict[str, Any]:
    if action == "delete_file":
        target = safe_workspace_path(root, str(args.get("name", "")))
        if not target.is_file():
            raise HTTPException(404, "File not found or not a regular file.")
        target.unlink()
        return {"ok": True, "result": f"Deleted {target.name}"}
    if action == "overwrite_text_file":
        target = safe_workspace_path(root, str(args.get("name", "")))
        if target.is_dir():
            raise HTTPException(400, "Cannot overwrite a directory.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(args.get("content", "")), encoding="utf-8")
        return {"ok": True, "result": f"Updated {target.relative_to(root)}"}
    if action == "run_blender_project":
        blender = os.environ.get("JARVIS_BLENDER_BIN") or shutil.which("blender")
        if not blender:
            return {"ok": False, "result": "No Blender command-line executable is available in Termux. The generated OBJ and Blender Python script are ready for import/open in the Android Blender app, but this worker cannot control that app directly."}
        project = safe_workspace_path(root, str(args.get("name", "")))
        script = (project / "scene.py").resolve()
        if project not in script.parents or not script.is_file():
            raise HTTPException(404, "Generated scene.py not found in that project.")
        result = subprocess.run([blender, "--background", "--python", str(script)], cwd=str(project),
                                capture_output=True, text=True, timeout=300, check=False)
        return {"ok": result.returncode == 0, "result": (result.stdout + "\n" + result.stderr)[-5000:],
                "return_code": result.returncode}
    raise HTTPException(400, "Unsupported approved action.")


def execute_tool(root: Path, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    if tool == "list_workspace":
        rows = []
        for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
            if p.name in ("agent-settings.json",):
                continue
            rows.append({"name": p.name, "type": "directory" if p.is_dir() else "file",
                         "size": p.stat().st_size if p.is_file() else None})
        return {"ok": True, "result": rows}
    if tool == "read_text_file":
        target = safe_workspace_path(root, str(args.get("name", "")))
        if not target.is_file():
            raise HTTPException(404, "File not found.")
        if target.stat().st_size > 128 * 1024:
            raise HTTPException(413, "Text file is larger than 128 KB.")
        return {"ok": True, "result": target.read_text(encoding="utf-8", errors="replace")}
    if tool == "create_text_file":
        target = safe_workspace_path(root, str(args.get("name", "")))
        if target.exists():
            approval = queue_approval(root, "overwrite_text_file", args, f"Overwrite existing file {target.name}")
            return {"ok": True, "pending_approval": approval, "result": "Waiting for approval to overwrite existing file."}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(args.get("content", "")), encoding="utf-8")
        return {"ok": True, "result": f"Created {target.relative_to(root)}"}
    if tool == "create_blender_scene":
        name = str(args.get("name") or "jarvis_scene")
        description = str(args.get("description") or "A stylized cinematic room")[:1000]
        result = build_scene_project(root, name, description)
        return {"ok": True, "result": result}
    if tool == "delete_file":
        target = safe_workspace_path(root, str(args.get("name", "")))
        approval = queue_approval(root, "delete_file", {"name": str(target.relative_to(root))},
                                  f"Delete {target.name}; this cannot be undone.")
        return {"ok": True, "pending_approval": approval, "result": "Deletion requires your approval."}
    if tool == "run_blender_project":
        name = str(args.get("name", ""))
        approval = queue_approval(root, "run_blender_project", {"name": name},
                                  "Execute the generated Blender scene script. This may create or overwrite a .blend project file.")
        return {"ok": True, "pending_approval": approval, "result": "Blender execution requires your approval."}
    return {"ok": False, "result": f"Tool not allowed: {tool}"}


def deterministic_fallback(root: Path, message: str) -> dict[str, Any]:
    lower = message.lower()
    if any(x in lower for x in ("create", "build", "make", "generate")) and any(
        x in lower for x in ("scene", "lab", "laboratory", "room", "environment", "studio", "workshop")
    ):
        name_match = re.search(r"(?:named|called)\s+([a-zA-Z0-9_-]+)", message, re.IGNORECASE)
        name = name_match.group(1) if name_match else "jarvis_scene"
        result = execute_tool(root, "create_blender_scene", {"name": name, "description": message})
        return {"reply": "I used the local CPU worker team to build a procedural scene package. It contains an OBJ preview, material file, scene specification and a Blender Python build script. This is a starter environment, not a finished photoreal character or cinematic.",
                "provider": "local_worker_fallback", "actions": [result],
                "worker_trace": ["Director: decomposed scene request", "Geometry Worker: created primitive layout",
                                 "Material Worker: assigned procedural materials", "World Worker: assembled room layout",
                                 "Cinematography Worker: added camera path and lighting plan", "Quality Worker: validated transforms"]}
    if any(x in lower for x in ("list files", "show files", "workspace files")):
        result = execute_tool(root, "list_workspace", {})
        return {"reply": "Here is the current worker workspace.", "provider": "local_worker_fallback", "actions": [result], "worker_trace": ["Workspace Worker: listed local files"]}
    return {"reply": "The local worker gateway is running, but no AI model answered this request. Start a local OpenAI-compatible GGUF server and set its model name, or configure a remote model API key for automatic fallback. I can still run the built-in CPU scene recipe when you ask me to create a room, lab, studio or environment.",
            "provider": "local_worker_fallback", "actions": [],
            "worker_trace": ["Local model: unavailable or not configured", "Remote model: unavailable or not configured", "Safe deterministic workers: ready"]}


async def handle_chat(root: Path, request: AgentChatRequest) -> dict[str, Any]:
    config = load_config(root)
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in request.history[-16:]:
        role = item.get("role", "")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:4000]})
    messages.append({"role": "user", "content": request.message})

    providers = []
    if config["local_base_url"] and config["local_model"]:
        providers.append(("local", config["local_base_url"], config["local_model"], ""))
    if config["remote_base_url"] and config["remote_model"] and config["remote_api_key"]:
        providers.append(("remote", config["remote_base_url"], config["remote_model"], config["remote_api_key"]))

    errors = []
    for provider, base, model, key in providers:
        try:
            content = await call_model(base, model, key, messages)
            plan = parse_plan(content)
            results = []
            traces = [f"Director model: {provider}"]
            for action in plan.get("actions", [])[:5] if isinstance(plan.get("actions", []), list) else []:
                if not isinstance(action, dict):
                    continue
                tool = str(action.get("tool", ""))
                args = action.get("arguments") if isinstance(action.get("arguments"), dict) else {}
                result = execute_tool(root, tool, args)
                results.append(result)
                if result.get("pending_approval"):
                    traces.append(f"Approval Worker: waiting for approval for {tool}")
                else:
                    traces.append(f"{tool}: completed" if result.get("ok") else f"{tool}: failed")
            return {"reply": str(plan.get("reply") or "Task processed."), "provider": provider,
                    "actions": results, "worker_trace": traces, "fallback_errors": errors}
        except Exception as exc:
            errors.append(f"{provider}: {type(exc).__name__}: {str(exc)[:300]}")
    fallback = deterministic_fallback(root, request.message)
    fallback["fallback_errors"] = errors
    return fallback

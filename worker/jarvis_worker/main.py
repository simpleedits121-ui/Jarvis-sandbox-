from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_ROOT = Path(os.environ.get("JARVIS_WORKSPACE", Path.home() / "storage" / "downloads" / "JARVIS_WORKSPACE")).resolve()
UPLOADS = APP_ROOT / "uploads"
OUTPUTS = APP_ROOT / "outputs"
JOBS = APP_ROOT / "jobs"
for folder in (APP_ROOT, UPLOADS, OUTPUTS, JOBS):
    folder.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("JARVIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
ACCESS_TOKEN = os.environ.get("JARVIS_ACCESS_TOKEN", "")
THREED_PROVIDER_URL = os.environ.get("JARVIS_3D_PROVIDER_URL", "").rstrip("/")
THREED_PROVIDER_TOKEN = os.environ.get("JARVIS_3D_PROVIDER_TOKEN", "")
LLM_BASE_URL = os.environ.get("JARVIS_LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.environ.get("JARVIS_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("JARVIS_LLM_MODEL", "")

app = FastAPI(title="JARVIS Sandbox Worker", version="0.3.0")
agent_tasks: dict[str, dict[str, Any]] = {}
three_d_jobs: dict[str, dict[str, Any]] = {}
for saved_job in JOBS.glob("3d-*.json"):
    try:
        row = json.loads(saved_job.read_text())
        three_d_jobs[row["job_id"]] = row
    except Exception:
        pass

def persist_3d_job(row: dict[str, Any]) -> None:
    (JOBS / f"3d-{row['job_id']}.json").write_text(json.dumps(row, indent=2))

def auth(authorization: str | None) -> None:
    # Loopback-only mode is safe for same-device use. Network binding requires a token.
    if HOST not in ("127.0.0.1", "localhost", "::1") and not ACCESS_TOKEN:
        raise HTTPException(503, "Set JARVIS_ACCESS_TOKEN before exposing the worker to a network.")
    if ACCESS_TOKEN and authorization != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(401, "Invalid worker token.")

def safe_path(name: str) -> Path:
    if name == "agent-settings.json":
        raise HTTPException(403, "Private agent credentials are not exposed through the file API.")
    if not name or name in (".", "..") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,127}", name):
        raise HTTPException(400, "Use a simple filename (letters, numbers, spaces, dot, underscore or hyphen).")
    target = (APP_ROOT / name).resolve()
    if target.parent != APP_ROOT:
        raise HTTPException(400, "Path escapes workspace.")
    return target

class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    confirm: bool = False

class AgentRequest(BaseModel):
    task: str = Field(min_length=3, max_length=4000)

@app.get("/health")
def health():
    try:
        brain = public_config(load_config(APP_ROOT))
    except Exception:
        brain = {"local_configured": False, "remote_configured": False}
    return {
        "ok": True,
        "service": "jarvis-sandbox-worker",
        "version": app.version,
        "workspace": str(APP_ROOT),
        "three_d_provider_configured": bool(THREED_PROVIDER_URL),
        "agent_brain": brain,
    }

@app.get("/api/v1/files")
def list_files(authorization: str | None = Header(default=None)):
    auth(authorization)
    rows = []
    for p in sorted(APP_ROOT.iterdir(), key=lambda x: x.name.lower()):
        if p.name == "agent-settings.json":
            continue
        rows.append({"name": p.name, "type": "directory" if p.is_dir() else "file",
                     "size": p.stat().st_size if p.is_file() else None})
    return {"files": rows}

@app.post("/api/v1/files")
async def upload_file(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    auth(authorization)
    raw_name = Path(file.filename or "upload.bin").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", raw_name).strip(" .")[:128] or "upload.bin"
    target = safe_path(name)
    data = await file.read()
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "Maximum upload size is 100 MB.")
    target.write_bytes(data)
    return {"name": target.name, "size": len(data)}

@app.get("/api/v1/files/{name}")
def read_file(name: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    target = safe_path(name)
    if not target.is_file():
        raise HTTPException(404, "File not found.")
    if target.stat().st_size > 2 * 1024 * 1024:
        raise HTTPException(413, "Use download endpoint for files over 2 MB.")
    return {"name": name, "content": target.read_text(errors="replace")}

@app.get("/api/v1/files/{name}/download")
def download_file(name: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    target = safe_path(name)
    if not target.is_file():
        raise HTTPException(404, "File not found.")
    return FileResponse(target, filename=target.name)

@app.delete("/api/v1/files/{name}")
def delete_file(name: str, confirm: bool = False, authorization: str | None = Header(default=None)):
    auth(authorization)
    if not confirm:
        raise HTTPException(409, "Deletion requires confirm=true.")
    target = safe_path(name)
    if not target.is_file():
        raise HTTPException(404, "File not found.")
    target.unlink()
    return {"deleted": name}

@app.post("/api/v1/commands")
def run_workspace_command(req: CommandRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    parts = req.command.strip().split(maxsplit=2)
    if not parts:
        raise HTTPException(400, "Empty command.")
    op = parts[0].lower()
    if op == "help":
        return {"output": "help | pwd | ls | touch NAME | mkdir NAME | write NAME TEXT | cat NAME | rm NAME (rm requires confirm=true)"}
    if op == "pwd":
        return {"output": str(APP_ROOT)}
    if op == "ls":
        return {"output": "\n".join(p.name for p in sorted(APP_ROOT.iterdir()))}
    if op in ("touch", "mkdir", "cat", "rm", "write"):
        if len(parts) < 2:
            raise HTTPException(400, "Filename required.")
        target = safe_path(parts[1])
        if op == "touch":
            target.touch(exist_ok=True)
            return {"output": f"Created {target.name}"}
        if op == "mkdir":
            target.mkdir(exist_ok=True)
            return {"output": f"Created directory {target.name}"}
        if op == "write":
            if len(parts) != 3:
                raise HTTPException(400, "Usage: write NAME TEXT")
            target.write_text(parts[2])
            return {"output": f"Wrote {target.stat().st_size} bytes"}
        if op == "cat":
            if not target.is_file():
                raise HTTPException(404, "File not found.")
            return {"output": target.read_text(errors="replace")[:12000]}
        if op == "rm":
            if not req.confirm:
                raise HTTPException(409, "Deletion requires confirm=true.")
            if not target.is_file():
                raise HTTPException(404, "File not found.")
            target.unlink()
            return {"output": f"Deleted {target.name}"}
    raise HTTPException(403, "Command not allowed. This worker does not expose an unrestricted shell.")

@app.post("/api/v1/agent/tasks")
def create_agent_task(req: AgentRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    task_id = str(uuid.uuid4())
    row = {"task_id": task_id, "task": req.task, "status": "queued",
           "created_at": int(time.time()),
           "note": "Task recorded. Connect an OpenAI-compatible model endpoint to enable AI planning."}
    agent_tasks[task_id] = row
    (JOBS / f"agent-{task_id}.json").write_text(json.dumps(row, indent=2))
    return row

@app.get("/api/v1/agent/tasks/{task_id}")
def get_agent_task(task_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if task_id not in agent_tasks:
        raise HTTPException(404, "Task not found.")
    return agent_tasks[task_id]

@app.get("/api/v1/3d/providers")
def three_d_providers(authorization: str | None = Header(default=None)):
    auth(authorization)
    return {
        "configured": bool(THREED_PROVIDER_URL),
        "provider_protocol": "JARVIS 3D Job API v1",
        "input": ["png", "jpg", "jpeg", "webp"],
        "outputs_expected": ["glb"],
        "note": "A compatible image-to-3D provider endpoint must be configured."
    }

@app.post("/api/v1/3d/jobs")
async def create_3d_job(image: UploadFile = File(...), prompt: str = Form(default="Create a complete textured 3D asset from this reference image."),
                        authorization: str | None = Header(default=None)):
    auth(authorization)
    suffix = Path(image.filename or "reference.png").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPException(415, "Upload PNG, JPG, JPEG or WEBP reference images.")
    raw = await image.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "Reference image limit is 20 MB.")
    job_id = str(uuid.uuid4())
    source = UPLOADS / f"{job_id}{suffix}"
    source.write_bytes(raw)
    job = {"job_id": job_id, "status": "received", "source": source.name,
           "created_at": int(time.time()), "outputs": [], "prompt": prompt}
    three_d_jobs[job_id] = job
    persist_3d_job(job)
    if not THREED_PROVIDER_URL:
        job["status"] = "needs_provider"
        job["message"] = "Image stored. Configure JARVIS_3D_PROVIDER_URL to run actual image-to-3D inference."
        persist_3d_job(job)
        return job
    headers = {}
    if THREED_PROVIDER_TOKEN:
        headers["Authorization"] = f"Bearer {THREED_PROVIDER_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            with source.open("rb") as stream:
                response = await client.post(
                    f"{THREED_PROVIDER_URL}/jobs",
                    headers=headers,
                    data={"prompt": prompt, "output_format": "glb"},
                    files={"image": (source.name, stream, image.content_type or "image/png")}
                )
        response.raise_for_status()
        provider_data = response.json()
        job["status"] = provider_data.get("status", "submitted")
        job["provider_job_id"] = provider_data.get("job_id") or provider_data.get("id")
        job["provider_response"] = provider_data
    except Exception as exc:
        job["status"] = "provider_error"
        job["message"] = f"Provider submission failed: {type(exc).__name__}: {exc}"
    persist_3d_job(job)
    return job

@app.get("/api/v1/3d/jobs/{job_id}")
async def get_3d_job(job_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    job = three_d_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found in this worker session.")
    provider_id = job.get("provider_job_id")
    if provider_id and THREED_PROVIDER_URL:
        headers = {}
        if THREED_PROVIDER_TOKEN:
            headers["Authorization"] = f"Bearer {THREED_PROVIDER_TOKEN}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{THREED_PROVIDER_URL}/jobs/{provider_id}", headers=headers)
            response.raise_for_status()
            data = response.json()
            job["status"] = data.get("status", job["status"])
            job["provider_response"] = data
            # Provider contract: outputs is a list of {url, filename}; worker downloads completed GLBs.
            for output in data.get("outputs", []):
                url = output.get("url")
                filename = Path(output.get("filename") or f"{job_id}.glb").name
                if url and filename.lower().endswith(".glb") and not any(x.get("filename") == filename for x in job["outputs"]):
                    async with httpx.AsyncClient(timeout=180) as client:
                        asset = await client.get(url)
                    asset.raise_for_status()
                    local = OUTPUTS / f"{job_id}-{filename}"
                    local.write_bytes(asset.content)
                    job["outputs"].append({"filename": local.name, "size": local.stat().st_size,
                                           "download": f"/api/v1/3d/jobs/{job_id}/outputs/{local.name}"})
        except Exception as exc:
            job["provider_poll_error"] = f"{type(exc).__name__}: {exc}"
    persist_3d_job(job)
    return job

@app.get("/api/v1/3d/jobs/{job_id}/outputs/{filename}")
def get_3d_output(job_id: str, filename: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.endswith(".glb"):
        raise HTTPException(400, "Invalid output name.")
    target = (OUTPUTS / safe_name).resolve()
    if target.parent != OUTPUTS.resolve() or not target.is_file():
        raise HTTPException(404, "Output not found.")
    return FileResponse(target, filename=safe_name, media_type="model/gltf-binary")


# --- JARVIS Swarm: model gateway, local workers and approval queue ---
from .agent import (
    AgentChatRequest, AgentConfigRequest, ApprovalRequest, handle_chat,
    load_config, public_config, save_config, pending_dir, list_approvals,
    run_approved_action,
)

@app.get("/api/v1/agent/config")
def get_agent_config(authorization: str | None = Header(default=None)):
    auth(authorization)
    return public_config(load_config(APP_ROOT))

@app.post("/api/v1/agent/config")
def update_agent_config(req: AgentConfigRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    config = load_config(APP_ROOT)
    for field in ("local_base_url", "local_model", "remote_base_url", "remote_model"):
        value = getattr(req, field).strip()
        if field.endswith("base_url") and value and not value.startswith(("http://", "https://")):
            raise HTTPException(400, f"{field} must start with http:// or https://")
        config[field] = value
    if req.clear_remote_key:
        config["remote_api_key"] = ""
    elif req.remote_api_key is not None and req.remote_api_key.strip():
        config["remote_api_key"] = req.remote_api_key.strip()
    save_config(APP_ROOT, config)
    return public_config(config)

@app.post("/api/v1/agent/chat")
async def agent_chat(req: AgentChatRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    return await handle_chat(APP_ROOT, req)

@app.get("/api/v1/agent/approvals")
def get_agent_approvals(authorization: str | None = Header(default=None)):
    auth(authorization)
    return {"approvals": list_approvals(APP_ROOT)}

@app.post("/api/v1/agent/approvals/{approval_id}")
def decide_agent_approval(approval_id: str, req: ApprovalRequest,
                          authorization: str | None = Header(default=None)):
    auth(authorization)
    path = (pending_dir(APP_ROOT) / f"{approval_id}.json").resolve()
    if path.parent != pending_dir(APP_ROOT).resolve() or not path.is_file():
        raise HTTPException(404, "Approval request not found.")
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("status") != "pending":
        raise HTTPException(409, "Approval request has already been handled.")
    if not req.approved:
        row["status"] = "rejected"
        row["result"] = "Rejected by user."
    else:
        result = run_approved_action(APP_ROOT, row["action"], row.get("arguments", {}))
        row["status"] = "approved"
        row["result"] = result
    path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row

@app.get("/api/v1/blender/status")
def blender_runtime_status(authorization: str | None = Header(default=None)):
    auth(authorization)
    binary = os.environ.get("JARVIS_BLENDER_BIN") or shutil.which("blender")
    return {"available": bool(binary), "binary": binary,
            "mode": "background Blender Python" if binary else "script-and-OBJ export only",
            "note": "The Android Blender app is a separate sandbox. Termux cannot silently control its UI or embedded Python unless that app exposes a compatible bridge."}

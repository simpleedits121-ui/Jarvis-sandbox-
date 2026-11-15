import os
import tempfile
from fastapi.testclient import TestClient

tmp = tempfile.mkdtemp(prefix="jarvis-worker-test-")
os.environ["JARVIS_WORKSPACE"] = tmp
os.environ["JARVIS_CONFIG_HOME"] = os.path.join(tmp, "private-config")
os.environ["JARVIS_HOST"] = "127.0.0.1"

from jarvis_worker.main import app
client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_safe_commands_and_file_lifecycle():
    assert client.post("/api/v1/commands", json={"command": "touch sample.txt"}).status_code == 200
    assert client.post("/api/v1/commands", json={"command": "write sample.txt hello"}).status_code == 200
    assert client.get("/api/v1/files/sample.txt").json()["content"] == "hello"
    assert client.post("/api/v1/commands", json={"command": "rm sample.txt"}).status_code == 409
    assert client.post("/api/v1/commands", json={"command": "rm sample.txt", "confirm": True}).status_code == 200

def test_reject_path_traversal_and_arbitrary_shell():
    assert client.get("/api/v1/files/..%2Fsecret").status_code in (400, 404)
    assert client.post("/api/v1/commands", json={"command": "sh -c id"}).status_code == 403

def test_image_job_requires_provider_but_records_upload():
    r = client.post("/api/v1/3d/jobs", files={"image": ("ref.png", b"fake-image", "image/png")})
    assert r.status_code == 200
    assert r.json()["status"] == "needs_provider"

def test_agent_config_does_not_return_api_key():
    response = client.post("/api/v1/agent/config", json={
        "local_base_url": "http://127.0.0.1:8080/v1",
        "local_model": "tiny-local",
        "remote_base_url": "https://api.openai.com/v1",
        "remote_model": "gpt-4o-mini",
        "remote_api_key": "test-secret-key",
    })
    assert response.status_code == 200
    assert response.json()["remote_configured"] is False
    fetched = client.get("/api/v1/agent/config")
    assert fetched.status_code == 200
    assert fetched.json()["remote_key_set"] is False
    assert "test-secret-key" not in fetched.text


def test_cpu_worker_creates_scene_package_without_model():
    response = client.post("/api/v1/agent/chat", json={
        "message": "Create a small anime laboratory scene with a desk, chair and cinematic lighting"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "local_worker_fallback"
    action = data["actions"][0]["result"]
    from pathlib import Path
    project = Path(action["path"])
    assert (project / "scene_spec.json").is_file()
    assert (project / "scene_preview.obj").is_file()
    script = (project / "scene.py").read_text()
    compile(script, str(project / "scene.py"), "exec")
    assert action["object_count"] >= 10


def test_destructive_action_waits_for_approval():
    from pathlib import Path
    root = Path(__import__("jarvis_worker.main", fromlist=["APP_ROOT"]).APP_ROOT)
    target = root / "approval-test.txt"
    target.write_text("keep me")
    response = client.post("/api/v1/agent/chat", json={
        "message": "Delete approval-test.txt"
    })
    # No model is configured; deletion is not guessed by the deterministic fallback.
    from jarvis_worker.agent import execute_tool
    result = execute_tool(root, "delete_file", {"name": "approval-test.txt"})
    approval = result["pending_approval"]
    assert target.exists()
    decision = client.post(f"/api/v1/agent/approvals/{approval['approval_id']}", json={"approved": False})
    assert decision.status_code == 200
    assert target.exists()


def test_local_model_failure_never_calls_remote(monkeypatch):
    import asyncio
    from jarvis_worker import agent
    root = __import__("jarvis_worker.main", fromlist=["APP_ROOT"]).APP_ROOT
    agent.save_config(root, {
        "local_base_url": "http://127.0.0.1:8080/v1", "local_model": "local",
        "remote_base_url": "https://example.invalid/v1", "remote_model": "remote",
        "remote_api_key": "secret",
    })
    calls = []
    async def fake_call(base, model, key, messages):
        calls.append(model)
        if model == "local":
            raise RuntimeError("local server offline")
        return '{"reply":"Remote fallback answered","actions":[]}'
    monkeypatch.setattr(agent, "call_model", fake_call)
    result = asyncio.run(agent.handle_chat(root, agent.AgentChatRequest(message="Hello JARVIS")))
    assert calls == ["local"]
    assert result.get("provider") != "remote"
    assert "local" in " ".join(result.get("worker_trace", [])).lower() or result.get("reply")


def test_approved_delete_executes_only_after_approval():
    from pathlib import Path
    root = Path(__import__("jarvis_worker.main", fromlist=["APP_ROOT"]).APP_ROOT)
    target = root / "approved-delete-test.txt"
    target.write_text("delete only after approval")
    from jarvis_worker.agent import execute_tool
    result = execute_tool(root, "delete_file", {"name": target.name})
    approval = result["pending_approval"]
    assert target.exists()
    decision = client.post(f"/api/v1/agent/approvals/{approval['approval_id']}", json={"approved": True})
    assert decision.status_code == 200
    assert not target.exists()


def test_agent_secret_file_is_not_readable_through_workspace_tools():
    assert client.get("/api/v1/files/agent-settings.json").status_code == 403
    from pathlib import Path
    from jarvis_worker.agent import safe_workspace_path
    from fastapi import HTTPException
    root = Path(__import__("jarvis_worker.main", fromlist=["APP_ROOT"]).APP_ROOT)
    try:
        safe_workspace_path(root, "agent-settings.json")
        assert False, "private settings should be blocked"
    except HTTPException as exc:
        assert exc.status_code == 403



def test_swarm_api_coordinates_agents_offline():
    created = client.post("/api/v1/swarm/tasks", json={"goal": "Design an anime character with a rig"})
    assert created.status_code == 200
    task = created.json()
    assert task["execution_mode"] == "offline_coordination"
    assert task["reasoning_available"] is False
    assert any(item["agent_id"] == "rigging" for item in task["subtasks"])
    ran = client.post(f"/api/v1/swarm/tasks/{task['task_id']}/run")
    assert ran.status_code == 200
    result = ran.json()
    assert result["status"] == "review"
    assert result["review"]["status"] == "needs_local_model_review"
    assert client.get(f"/api/v1/swarm/tasks/{task['task_id']}/messages").status_code == 200


def test_swarm_rejects_invalid_task_and_unknown_task():
    assert client.post("/api/v1/swarm/tasks", json={"goal": "x"}).status_code == 422
    assert client.get("/api/v1/swarm/tasks/not-a-real-id").status_code == 404


def test_swarm_agent_memory_is_available_after_run():
    created = client.post("/api/v1/swarm/tasks", json={"goal": "Plan character geometry"})
    task_id = created.json()["task_id"]
    client.post(f"/api/v1/swarm/tasks/{task_id}/run")
    memory = client.get("/api/v1/swarm/agents/geometry/memory")
    assert memory.status_code == 200
    assert memory.json()["entries"]

def test_character_forge_generates_real_local_glb_and_obj():
    response = client.post("/api/v1/character/generate", json={"character": "rem-inspired"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "generated"
    assert data["report"]["parts"] >= 15
    assert data["report"]["triangles"] >= 500
    job_id = data["job_id"]
    glb = client.get(f"/api/v1/character/{job_id}/jarvis_rem_character.glb")
    assert glb.status_code == 200
    assert glb.content[:4] == b"glTF"
    obj = client.get(f"/api/v1/character/{job_id}/jarvis_rem_character.obj")
    assert obj.status_code == 200
    assert b"o Head" in obj.content


def test_character_forge_rejects_unknown_preset():
    assert client.post("/api/v1/character/generate", json={"character": "unknown"}).status_code == 400


def test_character_forge_v06_has_smooth_geometry_and_detail_parts():
    from pathlib import Path
    from jarvis_worker.character_forge import generate_character
    target = Path(tmp) / "forge-v06-quality"
    report = generate_character(target)
    assert report["generator"].endswith("v0.6 smooth procedural geometry")
    assert report["parts"] >= 30
    assert report["vertices"] >= 15000
    assert report["triangles"] >= 25000
    assert report["materials"] >= 14
    assert "layered anime eyes with iris, pupils and highlights" in report["features"]
    assert "curved tapered hair locks and layered fringe" in report["features"]
    glb = (target / "jarvis_rem_character.glb").read_bytes()
    import struct, json
    magic, version, total = struct.unpack_from("<III", glb, 0)
    json_len, json_type = struct.unpack_from("<II", glb, 12)
    document = json.loads(glb[20:20 + json_len].decode().strip())
    assert magic == 0x46546C67 and version == 2 and total == len(glb)
    assert json_type == 0x4E4F534A
    assert len(document["meshes"]) >= 30
    assert all("NORMAL" in mesh["primitives"][0]["attributes"] for mesh in document["meshes"])

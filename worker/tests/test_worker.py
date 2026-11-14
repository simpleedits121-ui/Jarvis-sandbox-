import os
import tempfile
from fastapi.testclient import TestClient

tmp = tempfile.mkdtemp(prefix="jarvis-worker-test-")
os.environ["JARVIS_WORKSPACE"] = tmp
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

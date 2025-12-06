from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_root_page():
    r = client.get("/")
    assert r.status_code == 200

def test_get_latest_cache():
    r = client.get("/get-latest-cache")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"

def test_validate_md_upload(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("# Title\n\nContent.", encoding="utf-8")
    with md.open("rb") as f:
        files = {"file": (md.name, f, "text/markdown")}
        r = client.post("/validate-file", files=files, data={"file_type": "md"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["file_path"].endswith("x.md")
    assert data["preserve_structure"] is True

"""Comprehensive integration tests for Mitchell Studio Server and API surface."""

import pytest
from starlette.testclient import TestClient

from mitchell.studio.server import create_studio_app


@pytest.fixture
def client():
    app = create_studio_app()
    return TestClient(app)


def test_studio_index_serves_html(client):
    """Verify root / serves HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Mitchell Studio" in response.text or "Mitchell" in response.text


def test_api_state(client):
    """Verify /api/state returns full snapshot."""
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "blackboard" in data
    assert "cost" in data


def test_api_ide_file_tree(client):
    """Verify /api/ide returns directory tree and tool status."""
    response = client.get("/api/ide")
    assert response.status_code == 200
    data = response.json()
    assert "file_tree" in data
    assert "tools" in data
    assert data["file_tree"]["type"] == "directory"


def test_api_harness_catalog_and_start(client):
    """Verify /api/harness lists agents and starts task session."""
    # GET
    res = client.get("/api/harness")
    assert res.status_code == 200
    data = res.json()
    assert "supported_agents" in data
    assert len(data["supported_agents"]) >= 3

    # POST start simulated task
    post_res = client.post("/api/harness", json={
        "action": "start",
        "agent_id": "claude",
        "prompt": "Inspect codebase AST",
    })
    assert post_res.status_code == 200
    session_data = post_res.json()
    assert session_data["agent_name"] == "claude"
    assert session_data["status"] in ("running", "completed")


def test_api_documents_crud_and_report(client):
    """Verify /api/documents creates and generates structured reports."""
    # Generate report
    res = client.post("/api/documents", json={
        "action": "generate_report",
        "topic": "System Reliability Benchmark",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "generated"
    assert "document" in data
    assert "System Reliability Benchmark" in data["document"]["title"]

    # List documents
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    assert len(list_res.json()["documents"]) > 0


def test_api_deep_research(client):
    """Verify /api/research synthesizes multi-source query with citations."""
    res = client.post("/api/research", json={
        "query": "Autonomous Agentic IDE Architecture",
        "max_sources": 3,
    })
    assert res.status_code == 200
    data = res.json()
    assert "detailed_report" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
    assert len(data["key_findings"]) > 0


def test_api_iot_entities_and_service(client):
    """Verify /api/iot lists entities and processes service calls."""
    res = client.get("/api/iot")
    assert res.status_code == 200
    data = res.json()
    assert "entities" in data
    assert len(data["entities"]) > 0

    # Call service
    call_res = client.post("/api/iot", json={
        "domain": "light",
        "service": "turn_on",
        "entity_id": "light.living_room",
    })
    assert call_res.status_code == 200


def test_api_teaching_and_synthesis(client):
    """Verify /api/teaching synthesizes procedural skills from recorded actions."""
    res = client.post("/api/teaching", json={
        "action": "synthesize",
        "name": "quick_web_lookup",
        "description": "Taught web lookup procedure",
        "actions": [
            {
                "action_type": "tool",
                "target": "browser_goto",
                "params": {"url": "https://news.ycombinator.com"},
                "timestamp": 1700000000.0,
            }
        ],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["skill_name"] == "quick_web_lookup"
    assert "url" in data["parameters"]


def test_api_takeover_engine(client):
    """Verify /api/takeover starts session and advances steps."""
    res = client.post("/api/takeover", json={
        "action": "start",
        "goal": "Build payment webhook listener",
    })
    assert res.status_code == 200
    session = res.json()
    assert session["status"] == "running"
    assert len(session["steps"]) == 5

    # Advance
    adv_res = client.post("/api/takeover", json={
        "action": "advance",
        "session_id": session["session_id"],
        "success": True,
        "summary": "Completed inspection step",
    })
    assert adv_res.status_code == 200


def test_api_browser_real_profile(client):
    """Verify /api/browser/real scans user profiles."""
    res = client.get("/api/browser/real")
    assert res.status_code == 200
    data = res.json()
    assert "profiles" in data

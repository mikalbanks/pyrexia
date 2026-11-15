"""Published-data endpoints preserve provenance and recomputable results."""
from fastapi.testclient import TestClient
import pytest

from pyrexia.app import app
from pyrexia.braindance import verify_braindance_evidence


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PYREXIA_DATA_DIR", str(tmp_path / "records"))
    monkeypatch.delenv("PYREXIA_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("REPLIT_DEPLOYMENT", raising=False)
    with TestClient(app, raise_server_exceptions=False) as api:
        yield api


def test_published_status_discloses_actual_file_counts_and_provenance(client):
    response = client.get("/api/braindance")
    assert response.status_code == 200
    status = response.json()
    assert status["available"] is True
    assert status["run_count"] == 426
    assert status["organoid_count"] == 16
    source = status["source"]
    assert source["source_experiment_count"] == 38
    assert source["source_episode_count"] == 49796
    assert source["source_kind"] == "published_biological_recording_summary"
    assert source["license"] == "CC-BY-4.0"
    assert len(source["source_sha256"]) == 64
    assert "source reward units" in source["units"]
    assert "19 organoids" in status["limitations"][0]
    assert "16 organoid" in status["limitations"][0]


def test_default_analysis_uses_cycled_organoid_replicates(client):
    response = client.post("/api/braindance/analyze", json={})
    assert response.status_code == 200
    report = response.json()
    assert len(report["runs"]) == 426
    summary = report["summary"]
    assert summary["paradigm"] == "cycled"
    assert summary["total_runs"] == 426
    assert summary["selected_runs"] == 288
    assert summary["selected_organoids"] == 12
    assert summary["units"] == "source reward units"
    assert summary["comparisons"][0]["paired_organoid_count"] == 12
    assert summary["comparisons"][1]["paired_organoid_count"] == 9
    assert "Descriptive secondary analysis" in summary["interpretation"]
    assert "No claim of causal learning" in summary["interpretation"]


def test_published_evidence_endpoint_recomputes(client):
    response = client.get("/api/braindance/evidence?paradigm=cycled")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert verify_braindance_evidence(response.content)["verified"] is True
    result = client.post("/api/braindance/verify", json={})
    assert result.status_code == 200
    assert result.json()["verified"] is True
    assert result.json()["run_count"] == 426


def test_unknown_paradigm_is_rejected(client):
    assert client.post("/api/braindance/analyze", json={"paradigm": "live"}).status_code == 422
    assert client.get("/api/braindance/evidence?paradigm=live").status_code == 422

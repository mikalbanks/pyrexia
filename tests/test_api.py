"""API workflows exercise persistence, provenance, boundaries, and access gates."""

import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from fastapi.testclient import TestClient
import pytest

from pyrexia.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PYREXIA_DATA_DIR", str(tmp_path / "records"))
    monkeypatch.delenv("PYREXIA_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("REPLIT_DEPLOYMENT", raising=False)
    with TestClient(app, raise_server_exceptions=False) as api:
        yield api


def synthetic(client, **changes):
    response = client.post("/api/datasets/synthetic", json={"duration_s": 6, "n_channels": 2, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def run(client, dataset, **changes):
    response = client.post("/api/runs", json={"dataset_id": dataset["id"], "recipe": "signal_stability", **changes})
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, raw=b"timestamp_s,channel\n1,1\n0.1,0\n", **changes):
    return client.post("/api/datasets/upload", files={"file": ("original-recording.csv", raw, "text/csv")}, data={
        "name": "Partner recording", "duration_s": "2", "n_channels": "2", "confirmed_rights": "true", **changes,
    })


def test_native_finalspark_offline_csv_uses_explicit_recording_start(client):
    raw = b"Time,channel\n2026-01-01T00:00:01+00:00,1\n2026-01-01T00:00:00.250Z,0\n"
    response = upload(client, raw, source_kind="finalspark_upload", recording_start="2026-01-01T00:00:00Z")
    assert response.status_code == 201, response.text
    dataset = response.json()
    assert dataset["provenance"]["network_session"] is False
    assert dataset["provenance"]["verification"] == "unverified_user_assertion"
    assert dataset["source_kind"] == "finalspark_upload"
    detail = client.get(f"/api/datasets/{dataset['id']}").json()
    assert detail["events"] == [{"timestamp_s": 0.25, "channel": 0}, {"timestamp_s": 1.0, "channel": 1}]
    result = run(client, dataset)
    assert client.post(f"/api/runs/{result['id']}/verify").json()["verified"] is True
    with zipfile.ZipFile(io.BytesIO(client.get(f"/api/runs/{result['id']}/evidence").content)) as archive:
        assert archive.read("original_input.csv") == raw


@pytest.mark.parametrize("origin", ["", "2026-01-01T00:00:00", "invalid"])
def test_native_finalspark_offline_csv_rejects_missing_or_ambiguous_origin(client, origin):
    response = upload(client, b"Time,channel\n2026-01-01T00:00:01Z,0\n", source_kind="finalspark_upload", recording_start=origin)
    assert response.status_code == 422


def test_synthetic_run_export_verify_and_independent_recomputation(client, tmp_path):
    assert client.get("/api/health").json()["status"] == "ok"
    dataset = synthetic(client)
    assert dataset["source_kind"] == "synthetic"
    assert dataset["provenance"]["biological_evidence"] is False
    assert "events" not in dataset
    result = run(client, dataset, recipe="stimulus_response", name="Demonstration response")
    assert result["result"]["metrics"]["trial_count"] == len(dataset["stimuli_s"])
    assert result["source_kind"] == "synthetic"
    assert result["status"] == "completed"
    json.dumps(result, allow_nan=False)
    state = client.get("/api/state").json()
    assert len(state["runs"]) == len(state["datasets"]) == 1
    assert {template["id"] for template in state["templates"]} >= {"signal_stability", "stimulus_response"}
    detail = client.get(f"/api/runs/{result['id']}").json()
    assert detail["dataset"]["sha256"] == dataset["sha256"]
    verification = client.post(f"/api/runs/{result['id']}/verify")
    assert verification.status_code == 200
    assert verification.json()["verified"] is True
    evidence = client.get(f"/api/runs/{result['id']}/evidence")
    assert evidence.status_code == 200
    assert evidence.headers["content-type"] == "application/zip"
    path = tmp_path / "evidence.zip"
    path.write_bytes(evidence.content)
    command = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/verify_evidence.py"), str(path)], capture_output=True, text=True, timeout=10)
    assert command.returncode == 0, command.stdout + command.stderr
    assert json.loads(command.stdout)["checks"]["recomputed_result"] is True


def test_upload_preserves_exact_bytes_and_separates_user_provenance(client):
    original = b"\xef\xbb\xbftimestamp_s,channel,annotation\r\n1.00,1,test\r\n0.10,0,test\r\n"
    response = upload(client, original, source_kind="braindance_upload", citation="User-provided article", license="Authorized research use")
    assert response.status_code == 201, response.text
    dataset = response.json()
    assert dataset["provenance"]["verification"] == "unverified_user_assertion"
    assert dataset["provenance"]["original_sha256"] == hashlib.sha256(original).hexdigest()
    assert dataset["source_kind"] == "braindance_upload"
    assert "original_input_base64" not in dataset
    detail = client.get(f"/api/datasets/{dataset['id']}").json()
    assert detail["events"] == [{"timestamp_s": 0.1, "channel": 0}, {"timestamp_s": 1.0, "channel": 1}]
    assert detail["display_truncated"] is False
    result = run(client, dataset)
    evidence = client.get(f"/api/runs/{result['id']}/evidence").content
    with zipfile.ZipFile(io.BytesIO(evidence)) as archive:
        assert archive.read("original_input.csv") == original
        assert hashlib.sha256(archive.read("input.csv")).hexdigest() == dataset["sha256"]
        assert "original_input_base64" not in json.loads(archive.read("dataset.json"))
    verification = client.post(f"/api/runs/{result['id']}/verify").json()
    assert verification["verified"] is True, verification
    assert verification["checks"]["original_input_hash"] is True
    assert "original_input_base64" not in json.dumps(client.get("/api/state").json())


def test_upload_requires_rights_and_prevents_source_spoofing(client):
    assert upload(client, confirmed_rights="false").status_code == 422
    assert upload(client, source_kind="live_neurons").status_code == 422
    assert upload(client, source_kind="sdk_simulator").status_code == 422
    assert client.get("/api/state").json()["datasets"] == []


@pytest.mark.parametrize("raw", [
    b"timestamp,channel\n0.1,0\n",
    b"timestamp_s,channel,channel\n0.1,0,0\n",
    b"timestamp_s,channel\n0.1,0.5\n",
    b"timestamp_s,channel\n-0.1,0\n",
    b"timestamp_s,channel\n2,0\n",
    b"timestamp_s,channel\n0.1,2\n",
    b"timestamp_s,channel\nnan,0\n",
    b"timestamp_s,channel\ninf,0\n",
    b"timestamp_s,channel\n0.1,\n",
    b"\x80\x04binarypickle\x00\xff",
])
def test_malformed_or_out_of_bounds_csv_is_rejected(client, raw):
    response = upload(client, raw)
    assert response.status_code == 422, response.text
    assert isinstance(response.json()["detail"], str)
    assert client.get("/api/state").json()["datasets"] == []


@pytest.mark.parametrize("stimuli", ["not json", "null", "{}", "[true]", "[1,1]", "[2]", "[NaN]"])
def test_invalid_stimulus_metadata_does_not_persist(client, stimuli):
    assert upload(client, stimuli_s=stimuli).status_code == 422
    assert client.get("/api/state").json()["datasets"] == []


def test_empty_recording_retains_explicit_observation_duration(client):
    response = upload(client, b"timestamp_s,channel\n", duration_s="7.5", n_channels="3")
    assert response.status_code == 201
    result = run(client, response.json())
    assert result["result"]["metrics"]["duration_s"] == 7.5
    assert result["result"]["metrics"]["recording_channels"] == 3
    assert result["result"]["metrics"]["mean_rate_hz_per_channel"] == 0
    assert result["result"]["metrics"]["time_weighted_bin_rate_cv"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("changes", [{"duration_s": 0}, {"duration_s": 301}, {"n_channels": 0}, {"n_channels": 65}, {"baseline_hz": -1}, {"response_hz": 201}, {"seed": -1}, {"source_kind": "live"}])
def test_synthetic_request_bounds_and_extra_fields(client, changes):
    response = client.post("/api/datasets/synthetic", json=changes)
    assert response.status_code == 422


@pytest.mark.parametrize("body", ['{"duration_s":NaN}', '{"baseline_hz":Infinity}', '{"response_hz":-Infinity}'])
def test_nonfinite_json_numbers_return_validation_error(client, body):
    response = client.post("/api/datasets/synthetic", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422, response.text


def test_invalid_run_parameters_and_missing_stimulus_times(client):
    dataset = synthetic(client)
    for changes in [{"bin_s": 0}, {"recipe": "invented_method"}, {"baseline_window_s": 5}]:
        response = client.post("/api/runs", json={"dataset_id": dataset["id"], "recipe": "stimulus_response", **changes})
        assert response.status_code == 422, response.text
    uploaded = upload(client).json()
    response = client.post("/api/runs", json={"dataset_id": uploaded["id"], "recipe": "stimulus_response"})
    assert response.status_code == 422
    assert "stimuli_s" in response.json()["detail"]
    assert client.get("/api/state").json()["runs"] == []


def test_compare_reports_setting_and_source_mismatch_without_claiming_equivalence(client):
    dataset = synthetic(client)
    first = run(client, dataset)
    second = run(client, dataset, name="Independent repeat")
    matching = client.post("/api/compare", json={"run_ids": [first["id"], second["id"]]}).json()
    assert matching["comparable"] is True
    assert "do not establish" in matching["note"]
    fixture = client.post("/api/datasets/fixture", json={"kind": "finalspark"}).json()
    other = run(client, fixture, bin_s=2)
    mismatch = client.post("/api/compare", json={"run_ids": [first["id"], other["id"]]}).json()
    assert mismatch["comparable"] is False
    assert any("bin_s" in reason for reason in mismatch["reasons"])
    assert any("source_kind" in reason for reason in mismatch["reasons"])
    assert client.post("/api/compare", json={"run_ids": [first["id"], first["id"]]}).status_code == 422


@pytest.mark.parametrize("kind", ["finalspark", "braindance"])
def test_fixture_cannot_appear_as_a_biological_recording(client, kind):
    response = client.post("/api/datasets/fixture", json={"kind": kind})
    assert response.status_code == 201
    dataset = response.json()
    assert dataset["source_kind"] == "test_fixture"
    assert dataset["provenance"]["biological_evidence"] is False
    assert dataset["provenance"]["fixture_kind"] == kind
    assert "synthetic" in dataset["name"].lower()
    result = run(client, dataset)
    assert any("not evidence from living neurons" in warning for warning in result["result"]["warnings"])


def test_recordings_and_results_survive_new_client_session(client):
    dataset = synthetic(client)
    result = run(client, dataset)
    with TestClient(app, raise_server_exceptions=False) as reopened:
        assert reopened.get(f"/api/datasets/{dataset['id']}").json()["sha256"] == dataset["sha256"]
        assert reopened.get(f"/api/runs/{result['id']}").json()["result"] == result["result"]
        assert reopened.post(f"/api/runs/{result['id']}/verify").json()["verified"] is True


def test_unknown_records_are_404(client):
    for path in ["/api/datasets/unknown", "/api/runs/unknown", "/api/runs/unknown/evidence"]:
        assert client.get(path).status_code == 404
    assert client.post("/api/runs/unknown/verify").status_code == 404
    assert client.post("/api/runs", json={"dataset_id": "unknown", "recipe": "signal_stability"}).status_code == 404


def test_rules_based_planner_is_honest_and_no_paid_service_is_required(client):
    response = client.post("/api/plans", json={"objective": "Compare stimulus response across known trials"})
    assert response.status_code == 200
    assert response.json()["assistant_mode"] == "rules_based"
    assert response.json()["recipe"] == "stimulus_response"
    assert "No AI model" in response.json()["explanation"]


def test_authentication_protects_reads_writes_and_assets(client, monkeypatch):
    password = "research-demo-password"
    monkeypatch.setenv("PYREXIA_DEMO_PASSWORD", password)
    for path in ["/", "/api/health", "/api/state", "/assets/plotly.min.js"]:
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")
    assert client.post("/api/datasets/synthetic", json={}).status_code == 401
    assert client.get("/api/state", auth=("pyrexia", "incorrect")).status_code == 401
    assert client.get("/api/state", auth=("other", password)).status_code == 401
    assert client.get("/api/state", auth=("pyrexia", password)).status_code == 200


@pytest.mark.parametrize("authorization", ["Basic !!!", "Bearer arbitrary", "Basic " + base64.b64encode("研究者:password".encode()).decode()])
def test_malformed_or_unicode_authentication_is_rejected(client, monkeypatch, authorization):
    monkeypatch.setenv("PYREXIA_DEMO_PASSWORD", "research-demo-password")
    response = client.get("/api/health", headers={"Authorization": authorization})
    assert response.status_code == 401, response.text


def test_replit_deployment_fails_closed_until_strong_password_configured(client, monkeypatch):
    monkeypatch.setenv("REPLIT_DEPLOYMENT", "1")
    assert client.get("/api/health").status_code == 503
    monkeypatch.setenv("PYREXIA_DEMO_PASSWORD", "short")
    assert client.get("/api/health", auth=("pyrexia", "short")).status_code == 503
    monkeypatch.setenv("PYREXIA_DEMO_PASSWORD", "research-demo-password")
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", auth=("pyrexia", "research-demo-password")).status_code == 200


def test_cross_origin_mutations_and_oversized_requests_rejected(client):
    assert client.post("/api/datasets/synthetic", json={}, headers={"Origin": "https://other.example"}).status_code == 403
    assert client.post("/api/datasets/synthetic", json={}, headers={"Origin": "http://testserver"}).status_code == 201
    response = client.post("/api/datasets/synthetic", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": str(11 * 1024 * 1024)})
    assert response.status_code == 413

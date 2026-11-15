"""Single-user research demo API and workstation. No laboratory control endpoints."""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from pyrexia import __version__
from pyrexia.analysis import analyze
from pyrexia.evidence import events_csv, export_evidence, verify_evidence
from pyrexia.providers import FinalSparkReadOnlyAdapter, cortical_dataset, fixture_dataset, provider_status, synthetic_dataset
from pyrexia.braindance import published_status, published_report, export_braindance_evidence, verify_braindance_evidence

WEB = Path(__file__).parent / "web"
MAX_UPLOAD = 10 * 1024 * 1024
MAX_EVENTS = 250_000
TEMPLATES = [
    {"id": "stimulus_response", "name": "Stimulus response", "description": "Compare equal-exposure baseline and response windows. Descriptive analysis only."},
    {"id": "signal_stability", "name": "Signal stability", "description": "Measure firing-rate variability and recording drift; includes silent electrodes."},
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def storage_dir() -> Path:
    directory = Path(os.environ.get("PYREXIA_DATA_DIR", "data"))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@contextmanager
def database():
    with sqlite3.connect(storage_dir() / "pyrexia.sqlite3", timeout=20) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)")
        yield connection


def save_record(kind: str, value: dict) -> dict:
    with database() as connection:
        connection.execute("INSERT INTO records VALUES (?, ?, ?)", (value["id"], kind, json.dumps(value, allow_nan=False)))
    return value


def record(kind: str, identity: str) -> dict:
    with database() as connection:
        row = connection.execute("SELECT payload FROM records WHERE id=? AND kind=?", (identity, kind)).fetchone()
    if row is None:
        raise HTTPException(404, f"{kind.title()} not found")
    return json.loads(row[0])


def records(kind: str) -> list[dict]:
    with database() as connection:
        rows = connection.execute("SELECT payload FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)).fetchall()
    return [json.loads(row[0]) for row in rows]


def public_dataset(dataset: dict) -> dict:
    return {key: value for key, value in dataset.items() if key not in {"events", "original_input_base64"}}


def add_dataset(events: list[dict], metadata: dict, original: bytes | None = None, original_filename: str | None = None) -> dict:
    if len(events) > MAX_EVENTS:
        raise ValueError(f"A demo dataset can contain at most {MAX_EVENTS:,} events")
    duration = float(metadata["duration_s"])
    channels = metadata["n_channels"]
    if not math.isfinite(duration) or duration <= 0 or duration > 3600:
        raise ValueError("Recording duration must be greater than zero and at most 3600 seconds")
    if isinstance(channels, bool) or not isinstance(channels, int) or not 1 <= channels <= 1024:
        raise ValueError("Channel count must be an integer from 1 to 1024")
    normalized = []
    for event in events:
        stamp, channel = event["timestamp_s"], event["channel"]
        if isinstance(stamp, bool) or not math.isfinite(float(stamp)) or not 0 <= float(stamp) < duration:
            raise ValueError("Each timestamp_s must fall within the declared recording duration [0, duration_s)")
        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < channels:
            raise ValueError("Each channel must be a zero-based integer within the declared channel count")
        normalized.append({"timestamp_s": float(stamp), "channel": channel})
    normalized.sort(key=lambda event: (event["timestamp_s"], event["channel"]))
    stimuli = metadata.get("stimuli_s", [])
    if not isinstance(stimuli, list) or len(stimuli) > 10_000:
        raise ValueError("stimuli_s must be a JSON array of at most 10,000 times in seconds")
    if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 0 <= t < duration for t in stimuli):
        raise ValueError("Each stimulus time must fall within the recording duration")
    if len(set(stimuli)) != len(stimuli):
        raise ValueError("Stimulus times must be unique")
    dataset = {
        **metadata, "stimuli_s": sorted(stimuli), "id": str(uuid.uuid4()),
        "events": normalized, "event_count": len(normalized), "created_at": now(),
        "sha256": hashlib.sha256(events_csv(normalized)).hexdigest(),
    }
    if original is not None:
        dataset["original_input_base64"] = base64.b64encode(original).decode("ascii")
        dataset["original_filename"] = original_filename
        dataset["provenance"]["original_sha256"] = hashlib.sha256(original).hexdigest()
    save_record("dataset", dataset)
    return public_dataset(dataset)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SyntheticConfig(StrictModel):
    name: str = Field(default="Synthetic response demo", min_length=1, max_length=120)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    duration_s: float = Field(default=30, ge=1, le=300)
    n_channels: int = Field(default=8, ge=1, le=64)
    baseline_hz: float = Field(default=3, ge=0, le=200)
    response_hz: float = Field(default=12, ge=0, le=200)


class CorticalConfig(StrictModel):
    duration_s: float = Field(default=2, ge=0.1, le=10)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)


class FixtureConfig(StrictModel):
    kind: Literal["finalspark", "braindance"]


class Experiment(StrictModel):
    schema_version: Literal["pyrexia-experiment-v1"] = "pyrexia-experiment-v1"
    name: str = Field(default="Untitled experiment", min_length=1, max_length=120)
    recipe: Literal["stimulus_response", "signal_stability"]
    dataset_id: str = Field(min_length=1, max_length=40)
    bin_s: float = Field(default=1, ge=0.01, le=3600)
    baseline_window_s: float = Field(default=0.2, ge=0.001, le=10)
    response_window_s: float = Field(default=0.2, ge=0.001, le=10)
    notes: str = Field(default="", max_length=4000)


class Comparison(StrictModel):
    run_ids: list[str] = Field(min_length=2, max_length=4)


class Objective(StrictModel):
    objective: str = Field(min_length=4, max_length=1000)


app = FastAPI(title="Pyrexia Experiment API", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, description="Single-user research demo. No live laboratory controls.")


@app.middleware("http")
async def protect_demo(request: Request, call_next):
    password = os.environ.get("PYREXIA_DEMO_PASSWORD", "")
    deployed = os.environ.get("REPLIT_DEPLOYMENT", "").lower() in {"1", "true"}
    if deployed and len(password) < 12:
        return JSONResponse({"detail": "Set PYREXIA_DEMO_PASSWORD to at least 12 characters in Replit Secrets before deployment."}, status_code=503)
    if password:
        valid = False
        try:
            scheme, credentials = request.headers.get("authorization", " ").split(" ", 1)
            username, supplied = base64.b64decode(credentials, validate=True).decode("utf-8").split(":", 1)
            valid = scheme.lower() == "basic" and hmac.compare_digest(username.encode(), b"pyrexia") and hmac.compare_digest(supplied.encode(), password.encode())
        except (ValueError, UnicodeError):
            pass
        if not valid:
            return JSONResponse({"detail": "Sign in with username pyrexia and the configured demo password."}, status_code=401, headers={"WWW-Authenticate": 'Basic realm="Pyrexia Lab", charset="UTF-8"'})
    # Same-origin writes protect the unauthenticated local demo from browser form submissions.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host", ""):
            return JSONResponse({"detail": "Cross-origin writes are disabled"}, status_code=403)
        declared_length = request.headers.get("content-length", "0")
        try:
            if int(declared_length) > MAX_UPLOAD + 32_768:
                return JSONResponse({"detail": "Upload exceeds the 10 MiB demo limit"}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def bad_input(_request: Request, error: ValueError):
    return JSONResponse({"detail": str(error)}, status_code=422)


@app.get("/api/health")
def health():
    with database() as connection:
        connection.execute("SELECT 1")
    return {"status": "ok", "version": __version__, "mode": "single_user_research_demo"}


@app.get("/api/state")
def state():
    return {"version": __version__, "datasets": [public_dataset(d) for d in records("dataset")], "runs": records("run"), "providers": provider_status(), "templates": TEMPLATES}


@app.post("/api/datasets/synthetic", status_code=201)
def create_synthetic(config: SyntheticConfig):
    return add_dataset(*synthetic_dataset(config.model_dump()))


@app.post("/api/datasets/cortical", status_code=201)
def create_cortical(config: CorticalConfig):
    return add_dataset(*cortical_dataset(config.model_dump()))


@app.post("/api/datasets/fixture", status_code=201)
def create_fixture(config: FixtureConfig):
    return add_dataset(*fixture_dataset(config.kind))


@app.post("/api/datasets/upload", status_code=201)
async def upload_dataset(
    file: Annotated[UploadFile, File()], name: Annotated[str, Form(min_length=1, max_length=120)],
    duration_s: Annotated[float, Form(gt=0, le=3600)], n_channels: Annotated[int, Form(ge=1, le=1024)],
    stimuli_s: Annotated[str, Form()] = "[]", citation: Annotated[str, Form(max_length=2000)] = "",
    license: Annotated[str, Form(max_length=1000)] = "", source_kind: Annotated[str, Form()] = "uploaded",
    recording_start: Annotated[str, Form(max_length=100)] = "",
    confirmed_rights: Annotated[bool, Form()] = False,
):
    if source_kind not in {"uploaded", "braindance_upload", "finalspark_upload"}:
        raise ValueError("Unsupported recording source")
    if not confirmed_rights:
        raise ValueError("Confirm you have permission to analyze the recording")
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "CSV exceeds the 10 MiB demo limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Upload a UTF-8 CSV, not a pickle or binary recording") from exc
    reader = csv.DictReader(io.StringIO(text))
    native_finalspark = source_kind == "finalspark_upload" and {"Time", "channel"}.issubset(reader.fieldnames or []) and "timestamp_s" not in (reader.fieldnames or [])
    if not reader.fieldnames or not ({"timestamp_s", "channel"}.issubset(reader.fieldnames) or native_finalspark):
        raise ValueError("CSV needs timestamp_s and channel columns (seconds, zero-based electrode id); FinalSpark imports also accept Time,channel with an explicit recording_start")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("CSV has duplicate column names")
    events, raw_rows = [], []
    for index, row in enumerate(reader, start=2):
        if len(events) + len(raw_rows) >= MAX_EVENTS:
            raise ValueError(f"CSV exceeds {MAX_EVENTS:,} events")
        if native_finalspark:
            raw_rows.append(row)
            continue
        try:
            events.append({"timestamp_s": float(row["timestamp_s"]), "channel": int(row["channel"])})
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Invalid timestamp_s or integer channel on CSV row {index}") from exc
    try:
        stimuli = json.loads(stimuli_s)
    except json.JSONDecodeError as exc:
        raise ValueError("stimuli_s must be a JSON array of times in seconds") from exc
    provider_provenance = {}
    if native_finalspark:
        events, provider_metadata = FinalSparkReadOnlyAdapter().normalize(raw_rows, recording_start=recording_start, duration_s=duration_s, n_channels=n_channels, name=name)
        provider_provenance = provider_metadata["provenance"]
    metadata = {"name": name, "source_kind": source_kind, "duration_s": duration_s, "n_channels": n_channels, "stimuli_s": stimuli,
                "provenance": {"type": "user_supplied_recording", "verification": "unverified_user_assertion", "citation": citation, "license": license, "rights_confirmed_by_uploader": True,
                               **provider_provenance, "normalization": "timestamp_s seconds; channel zero-based; sorted by timestamp and channel", "note": "Pyrexia validates data structure, not biological origin or study authenticity."}}
    return add_dataset(events, metadata, raw, Path(file.filename or "recording.csv").name)


@app.get("/api/datasets/{identity}")
def get_dataset(identity: str):
    dataset = record("dataset", identity)
    return {**public_dataset(dataset), "events": dataset["events"][:10_000], "display_truncated": len(dataset["events"]) > 10_000}


@app.post("/api/runs", status_code=201)
def create_run(spec: Experiment):
    dataset = record("dataset", spec.dataset_id)
    parameters = spec.model_dump()
    start = time.perf_counter()
    result = analyze(dataset["events"], public_dataset(dataset), parameters)
    run = {"id": str(uuid.uuid4()), "name": spec.name, "dataset_id": dataset["id"], "dataset_name": dataset["name"],
           "source_kind": dataset["source_kind"], "created_at": now(), "spec": parameters, "result": result,
           "runtime_ms": round((time.perf_counter() - start) * 1000, 3), "engine_version": __version__, "status": "completed"}
    return save_record("run", run)


@app.get("/api/runs/{identity}")
def get_run(identity: str):
    run = record("run", identity)
    return {**run, "dataset": public_dataset(record("dataset", run["dataset_id"]))}


def run_bundle(identity: str) -> bytes:
    run = record("run", identity)
    return export_evidence(record("dataset", run["dataset_id"]), run["spec"], run["result"], {key: value for key, value in run.items() if key not in {"spec", "result"}})


@app.get("/api/runs/{identity}/evidence")
def get_evidence(identity: str):
    return Response(run_bundle(identity), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="pyrexia-evidence-{identity}.zip"'})


@app.post("/api/runs/{identity}/verify")
def verify_run(identity: str):
    return verify_evidence(run_bundle(identity))


@app.post("/api/compare")
def compare_runs(body: Comparison):
    if len(set(body.run_ids)) != len(body.run_ids):
        raise ValueError("Select distinct experiment runs")
    runs = [record("run", identity) for identity in body.run_ids]
    datasets = [record("dataset", run["dataset_id"]) for run in runs]
    reasons = []
    for key in ("recipe", "bin_s", "baseline_window_s", "response_window_s"):
        if len({run["spec"][key] for run in runs}) != 1:
            reasons.append(f"Different {key} settings")
    for key in ("source_kind", "duration_s", "n_channels", "stimuli_s"):
        if len({json.dumps(dataset[key], sort_keys=True) for dataset in datasets}) != 1:
            reasons.append(f"Different {key} across datasets")
    return {"runs": runs, "comparable": not reasons, "reasons": reasons,
            "note": "Side-by-side descriptive metrics. Matching settings do not establish equivalent biological preparations, biological learning, or comparative computing performance."}


@app.post("/api/plans")
def plan(body: Objective):
    objective = body.objective.lower()
    response = any(term in objective for term in ("stim", "response", "evoked"))
    recipe = "stimulus_response" if response else "signal_stability"
    return {"assistant_mode": "rules_based", "recipe": recipe, "name": body.objective[:100], "bin_s": 1.0,
            "baseline_window_s": 0.2, "response_window_s": 0.2,
            "explanation": "A keyword-based template suggestion; review the method and dataset before running. No AI model or scientific hypothesis validation is performed.",
            "requirements": ["Explicit recording duration and channel count", "Known stimulus times and nonoverlapping complete windows" if response else "Comparable recording conditions when assessing drift"]}


class BrainDanceRequest(StrictModel):
    paradigm: Literal["cycled", "continuous", "all"] = "cycled"


@app.get("/api/braindance")
def braindance_status():
    status = published_status()
    return {**status, "available": status["ready"], "limitations": status.get("source", {}).get("limitations", [])}


@app.post("/api/braindance/analyze")
def braindance_analysis(config: BrainDanceRequest):
    report = published_report(config.paradigm)
    return {**report, "limitations": report["source"]["limitations"]}


@app.get("/api/braindance/evidence")
def braindance_evidence(paradigm: Literal["cycled", "continuous", "all"] = "cycled"):
    return Response(export_braindance_evidence(paradigm), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="pyrexia-braindance-{paradigm}-evidence.zip"'})


@app.post("/api/braindance/verify")
def braindance_verification(config: BrainDanceRequest):
    return verify_braindance_evidence(export_braindance_evidence(config.paradigm))


@app.get("/assets/plotly.min.js")
def plotly_script():
    from plotly.offline import get_plotlyjs
    return Response(get_plotlyjs(), media_type="application/javascript")


@app.get("/")
def home():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/assets", StaticFiles(directory=WEB), name="assets")

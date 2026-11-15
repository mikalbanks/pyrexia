"""Offline data sources and a strictly simulator-only optional Cortical adapter.

This module performs no lab-network or hardware operations. Provider availability
is a capability declaration, not a claim that biological evidence was acquired.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from importlib import metadata as packages
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

import numpy as np


CL_VERSION = "1.0.0"
CL_DOCS = "https://docs.corticallabs.com/"
FS_DOCS = "https://finalspark-np.github.io/np-docs/np_core/doc_v2.html"
MAX_EVENTS = 250_000


def _number(value, name, minimum, maximum) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number between {minimum} and {maximum}.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return result


def _integer(value, name, minimum, maximum) -> int:
    result = _number(value, name, minimum, maximum)
    if result != int(result):
        raise ValueError(f"{name} must be an integer.")
    return int(result)


def _sdk_version() -> str | None:
    try:
        return packages.version("cl-sdk")
    except packages.PackageNotFoundError:
        return None


def provider_status() -> list[dict]:
    version = _sdk_version()
    from .braindance import published_status
    published = published_status()
    return [
        {
            "id": "synthetic", "name": "Pyrexia synthetic engine", "status": "available",
            "label": "Available · synthetic", "kind": "synthetic",
            "description": "Seeded Poisson spike data with programmed response windows. Software demonstration only; no biological learning claim.",
            "documentation_url": "https://numpy.org/doc/stable/reference/random/generator.html",
        },
        {
            "id": "cortical", "name": "Cortical Labs SDK simulator",
            "status": "available" if version == CL_VERSION else "optional_dependency",
            "label": "SDK installed · simulation only" if version == CL_VERSION else "Optional research dependency",
            "kind": "sdk_simulator", "sdk_version": version,
            "description": f"Requires cl-sdk=={CL_VERSION} and Python 3.12+. The adapter verifies simulator mode before opening. CC BY-NC 4.0; the default random source does not learn or respond to stimulation.",
            "documentation_url": CL_DOCS,
            "license": "CC BY-NC 4.0",
            "license_url": "https://github.com/Cortical-Labs/cl-sdk/blob/main/LICENSE",
        },
        {
            "id": "finalspark", "name": "FinalSpark offline adapter", "status": "available",
            "label": "Offline export normalization · test fixture", "kind": "offline_adapter",
            "description": "Normalizes documented Time/channel rows using an explicit UTC recording start. Fixture data is generated locally. No authorized SDK network session is implemented.",
            "documentation_url": FS_DOCS,
        },
        {
            "id": "braindance", "name": "Published BrainDance outcomes", "status": "available" if published["ready"] else "unavailable",
            "label": "Published summaries · offline" if published["ready"] else "Published summaries unavailable", "kind": "published_recording_summary",
            "description": "Hash-checked published trial-performance summaries, organoid-level comparisons and an independent evidence export. Processed outcomes are separate from normalized spike-recording imports and generated test fixtures.",
            "documentation_url": "https://zenodo.org/records/17684862",
        },
        {
            "id": "finalspark_live", "name": "FinalSpark NeuroPlatform live", "status": "access_required",
            "label": "Provider access required", "kind": "live_hardware",
            "description": "Requires provider authorization, lab connectivity and validated SDK configuration. No live-control implementation or credentials in this MVP. Public viewing is available on FinalSpark's website; service availability is not guaranteed.",
            "documentation_url": "https://finalspark.com/neuroplatform/",
            "viewer_url": "https://finalspark.com/live/",
        },
        {
            "id": "cortical_live", "name": "Cortical Labs CL1 live", "status": "access_required",
            "label": "Device or cloud access required", "kind": "live_hardware",
            "description": "Live CL1 requires authorized device/cloud access. This MVP deliberately only executes the verified local SDK simulator.",
            "documentation_url": CL_DOCS,
        },
    ]


def synthetic_dataset(config: dict) -> tuple[list[dict], dict]:
    """Generate an inhomogeneous Poisson process with explicit stimulus timing.

    Baseline and programmed response regions are disjoint. Response rates are
    generator inputs, not fitted biological effects. Recording duration remains
    explicit even for a silent channel or a completely empty event list.
    """
    seed = _integer(config.get("seed", 42), "seed", 0, 2**32 - 1)
    duration = _number(config.get("duration_s", 30), "duration_s", 1, 300)
    channels = _integer(config.get("n_channels", 8), "n_channels", 1, 64)
    baseline = _number(config.get("baseline_hz", 3), "baseline_hz", 0, 200)
    response = _number(config.get("response_hz", 12), "response_hz", 0, 200)
    name = str(config.get("name", "Synthetic response demo")).strip()
    if not name or len(name) > 160:
        raise ValueError("Dataset name must contain 1–160 characters.")
    # 200-ms responses every three seconds; leave room for a baseline first.
    stimuli = [float(t) for t in np.arange(1.0, duration - 0.2, 3.0)]
    intervals = []
    cursor = 0.0
    for onset in stimuli:
        if onset > cursor:
            intervals.append((cursor, onset, baseline))
        intervals.append((onset, onset + 0.2, response))
        cursor = onset + 0.2
    if cursor < duration:
        intervals.append((cursor, duration, baseline))
    expected = channels * sum((end - start) * rate for start, end, rate in intervals)
    if expected > MAX_EVENTS * 0.9:
        raise ValueError("Requested dataset is too large. Reduce duration, channels or rates.")
    rng = np.random.default_rng(seed)
    events = []
    for channel in range(channels):
        for start, end, rate in intervals:
            count = int(rng.poisson((end - start) * rate))
            if len(events) + count > MAX_EVENTS:
                raise ValueError("Generated event limit exceeded; reduce dataset size.")
            for t in rng.uniform(start, end, count):
                events.append({"timestamp_s": float(t), "channel": channel})
    events.sort(key=lambda event: (event["timestamp_s"], event["channel"]))
    params = {"seed": seed, "duration_s": duration, "n_channels": channels,
              "baseline_hz": baseline, "response_hz": response, "response_window_s": 0.2}
    return events, {
        "name": name, "duration_s": duration, "n_channels": channels,
        "stimuli_s": stimuli, "source_kind": "synthetic",
        "provenance": {
            "mode": "synthetic", "biological_evidence": False,
            "generator": "Pyrexia inhomogeneous Poisson generator v1",
            "generation_parameters": params, "numpy_version": np.__version__,
            "verified_facts": ["Data generated locally from recorded parameters."] ,
            "limitations": ["Response windows and rates are programmed generator inputs.",
                            "No tissue, provider hardware, learning or biological efficacy is demonstrated."],
        },
    }


def _utc_datetime(value, name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO-8601 timestamp with UTC offset.") from exc
    else:
        raise ValueError(f"{name} must be an ISO-8601 string or timezone-aware datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} requires an explicit timezone; naive timestamps are not accepted.")
    return parsed.astimezone(timezone.utc)


class FinalSparkReadOnlyAdapter:
    """Normalize authorized offline exports; never connects to a laboratory.

    `Time` is documented as a datetime by FinalSpark. Numeric epochs are rejected
    because their units cannot safely be guessed. Dataset origin and observation
    duration are supplied by the user rather than inferred from first/last spikes.
    """

    @staticmethod
    def readiness() -> dict:
        return {"offline_normalization": True, "network_implemented": False,
                "authorized_live_session": False, "credentials_required_for_offline": False,
                "documentation_url": FS_DOCS}

    def normalize(self, rows, *, recording_start, duration_s, n_channels,
                  name="FinalSpark offline export") -> tuple[list[dict], dict]:
        start = _utc_datetime(recording_start, "recording_start")
        duration = _number(duration_s, "duration_s", 0.001, 86_400)
        channels = _integer(n_channels, "n_channels", 1, 4096)
        events = []
        for index, row in enumerate(rows):
            if index >= MAX_EVENTS:
                raise ValueError("Export exceeds the event limit.")
            if not isinstance(row, dict) or "Time" not in row or "channel" not in row:
                raise ValueError(f"Row {index + 1} requires Time and channel columns.")
            timestamp = (_utc_datetime(row["Time"], f"Row {index + 1} Time") - start).total_seconds()
            channel = _integer(row["channel"], f"Row {index + 1} channel", 0, channels - 1)
            if not 0 <= timestamp < duration:
                raise ValueError(f"Row {index + 1} Time lies outside the explicit recording interval.")
            events.append({"timestamp_s": timestamp, "channel": channel})
        events.sort(key=lambda event: (event["timestamp_s"], event["channel"]))
        return events, {
            "name": str(name), "duration_s": duration, "n_channels": channels,
            "stimuli_s": [], "source_kind": "finalspark_upload",
            "provenance": {
                "mode": "offline_export", "recording_start_utc": start.isoformat(),
                "documentation_url": FS_DOCS, "network_session": False,
                "user_assertions": ["Caller identifies these rows as a FinalSpark export."],
                "verified_facts": ["Timestamp, channel and recording-interval validation passed."],
                "limitations": ["Normalization does not authenticate recording origin or biological claims."],
            },
        }


def fixture_dataset(kind: str) -> tuple[list[dict], dict]:
    if kind not in {"finalspark", "braindance"}:
        raise ValueError("Fixture kind must be finalspark or braindance.")
    label = "FinalSpark" if kind == "finalspark" else "BrainDance"
    events, metadata = synthetic_dataset({"seed": 1701 if kind == "finalspark" else 2026,
                                          "duration_s": 20, "n_channels": 8,
                                          "baseline_hz": 2, "response_hz": 10})
    synthetic_provenance = metadata["provenance"]
    if kind == "finalspark":
        recording_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [{"Time": (recording_start + timedelta(seconds=e["timestamp_s"])).isoformat(),
                 "channel": e["channel"]} for e in events]
        events, normalized = FinalSparkReadOnlyAdapter().normalize(
            rows, recording_start=recording_start, duration_s=metadata["duration_s"],
            n_channels=metadata["n_channels"])
        metadata["provenance"] = normalized["provenance"]
    metadata.update(name=f"{label} format test fixture · synthetic", source_kind="test_fixture")
    metadata["provenance"].update({
        "mode": "test_fixture", "fixture_kind": kind, "biological_evidence": False,
        "generation_parameters": synthetic_provenance["generation_parameters"],
        "generator": synthetic_provenance["generator"],
        "numpy_version": synthetic_provenance["numpy_version"],
        "user_assertions": [],
        "verified_facts": ["Representative fixture generated locally; not provider-recorded activity."],
        "limitations": ["Generated test data for demonstrating import normalization and analysis.",
                        "This is not a recording from FinalSpark, BrainDance or living tissue."],
    })
    return events, metadata


def cortical_dataset(config: dict) -> tuple[list[dict], dict]:
    duration = _number(config.get("duration_s", 2), "duration_s", 0.1, 10)
    seed = _integer(config.get("seed", 42), "seed", 0, 2**32 - 1)
    version = _sdk_version()
    if version != CL_VERSION:
        raise ValueError(f"Optional simulator requires cl-sdk=={CL_VERSION} (CC BY-NC 4.0); installed version: {version or 'none'}. Install the research extra using Python 3.12+.")
    worker = Path(__file__).with_name("_cortical_worker.py")
    # Ignore inherited custom/replay/live sources and dotenv configuration.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("CL_") and key not in {"PYTHONPATH", "PYTHONSTARTUP"}}
    env.update(CL_SDK_VISUALISATION="0", CL_SDK_WEBSOCKET="0", CL_SDK_ACCELERATED_TIME="1",
               CL_SDK_RANDOM_SEED=str(seed), CL_SDK_REPLAY_START_OFFSET="0", PYTHON_DOTENV_DISABLED="1")
    with tempfile.TemporaryDirectory(prefix="pyrexia-cortical-") as folder:
        process = subprocess.Popen(
            [sys.executable, "-I", str(worker), str(duration), str(seed)], cwd=folder,
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ValueError("Cortical SDK simulator exceeded the 30-second acquisition limit.") from exc
        if process.returncode:
            # Worker messages are deliberately short and never contain credentials.
            error_path = Path(folder, "error.json")
            if error_path.exists():
                detail = json.loads(error_path.read_text())["error"]
            else:
                detail = "Simulator process failed. Check optional dependency compatibility."
            raise ValueError(detail)
        try:
            payload = json.loads(Path(folder, "result.json").read_text())
        except (OSError, ValueError) as exc:
            raise ValueError("Simulator did not produce a valid acquisition result.") from exc
    return payload["events"], {
        "name": "Cortical SDK random simulation", "duration_s": duration,
        "n_channels": payload["n_channels"], "stimuli_s": [], "source_kind": "sdk_simulator",
        "provenance": {
            "mode": "cortical_sdk_simulation", "biological_evidence": False,
            "sdk": "cl-sdk", "sdk_version": version, "simulator_verified": True,
            "documentation_url": CL_DOCS, "license": "CC BY-NC 4.0",
            "generation_parameters": {"seed": seed, "duration_s": duration,
                                      "frames_per_second": payload["frames_per_second"],
                                      "start_offset_frames": 0,
                                      "ticks_per_second": 100, "accelerated_time": True},
            "verified_facts": ["Official SDK reported simulator mode before connection.",
                               "Acquisition used the SDK default random source without hardware or stimulation calls."],
            "limitations": ["Synthetic non-learning control data; no biological learning or response to stimulation.",
                            "Optional SDK is licensed for noncommercial use under CC BY-NC 4.0."],
        },
    }

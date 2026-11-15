"""Portable, integrity-checked evidence packages without executing archive code."""

from __future__ import annotations

import csv
import base64
import hashlib
import io
import json
import platform
import zipfile
from pathlib import Path, PurePosixPath

from .analysis import ENGINE_VERSION, analyze, normalized_events

SCHEMA_VERSION = "pyrexia-evidence-v1"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_EVENTS = 250_000


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")


def events_csv(events: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["timestamp_s", "channel"])
    for event in sorted(events, key=lambda event: (float(event["timestamp_s"]), int(event["channel"]))):
        writer.writerow([repr(float(event["timestamp_s"])), int(event["channel"])])
    return output.getvalue().encode("utf-8")


def _analysis_source() -> bytes:
    return Path(__file__).with_name("analysis.py").read_bytes()


def export_evidence(dataset: dict, spec: dict, result: dict, run_metadata: dict) -> bytes:
    """Archive complete inputs, engine source, results and content hashes.

    Integrity hashes are not signatures, proof of biological provenance, or
    assurance that supplied acquisition metadata is accurate.
    """
    metadata = {key: value for key, value in dataset.items() if key not in {"events", "display_truncated", "original_input_base64"}}
    events = normalized_events(dataset["events"], float(metadata["duration_s"]), int(metadata["n_channels"]))
    input_bytes = events_csv(events)
    metadata["evidence_input_sha256"] = hashlib.sha256(input_bytes).hexdigest()
    files = {
        "input.csv": input_bytes,
        "dataset.json": canonical_json(metadata),
        "experiment.json": canonical_json(spec),
        "result.json": canonical_json(result),
        "analysis.py": _analysis_source(),
        "run.json": canonical_json(run_metadata),
        "environment.json": canonical_json({
            "schema_version": SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "python_version": platform.python_version(),
            "dependencies": "Python standard library only for the bundled analysis engine",
        }),
        "requirements.txt": b"# Bundled analysis.py uses only the Python 3.12 standard library.\n",
        "README.md": (
            "# Pyrexia experiment evidence\n\n"
            "Inputs use seconds and zero-based channel indices. Dataset duration and configured channel count are explicit. "
            "Results are descriptive and include all input events; a display raster may be truncated.\n\n"
            "To verify safely, use a trusted Pyrexia checkout: `python scripts/verify_evidence.py evidence.zip`. "
            "The verifier checks every payload hash and recomputes using its trusted engine, only when bundled source matches. "
            "It never executes code from an untrusted archive. No provider account, SDK or network access is needed.\n\n"
            "SHA-256 proves payload integrity relative to this manifest, not authenticity of recordings, user-supplied provenance, "
            "biological origin, learning, or an author's identity. Anyone can modify files and recalculate an unsigned manifest. "
            "Preserve acquisition records independently.\n"
        ).encode("utf-8"),
    }
    if dataset.get("original_input_base64") is not None:
        original_bytes = base64.b64decode(dataset["original_input_base64"], validate=True)
        original_hash = metadata.get("provenance", {}).get("original_sha256")
        if hashlib.sha256(original_bytes).hexdigest() != original_hash:
            raise ValueError("Original input bytes do not match provenance.original_sha256.")
        files["original_input.csv"] = original_bytes
    manifest = {"schema_version": SCHEMA_VERSION, "files": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
    files["manifest.json"] = canonical_json(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def verify_evidence(content: bytes) -> dict:
    """Return a machine-readable check result; never extract or execute payloads."""
    checks: dict[str, bool] = {}
    details: list[str] = []
    try:
        if len(content) > MAX_ARCHIVE_BYTES:
            raise ValueError("Archive exceeds the 32 MiB verification limit.")
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("Archive contains duplicate paths.")
            if len(infos) > 32 or sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
                raise ValueError("Archive exceeds expansion/file-count limits.")
            if any(info.filename == "input.csv" and info.file_size > MAX_INPUT_BYTES for info in infos):
                raise ValueError("Normalized input CSV exceeds the 32 MiB verification limit.")
            if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts or "\\" in name or name.endswith("/") for name in names):
                raise ValueError("Archive contains an unsafe path.")
            files = {name: archive.read(name) for name in names}
        required = {"manifest.json", "input.csv", "dataset.json", "experiment.json", "result.json", "analysis.py", "run.json", "environment.json", "requirements.txt", "README.md"}
        checks["required_files"] = required.issubset(files)
        if not checks["required_files"]:
            raise ValueError("Required evidence files are missing.")
        checks["allowed_files"] = set(files).issubset(required | {"original_input.csv"})
        if not checks["allowed_files"]:
            raise ValueError("Archive contains unexpected files.")
        manifest = json.loads(files["manifest.json"])
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object.")
        checks["schema"] = manifest.get("schema_version") == SCHEMA_VERSION
        declared = manifest.get("files")
        if not isinstance(declared, dict):
            raise ValueError("Manifest files must be a mapping.")
        checks["complete_manifest"] = set(declared) == set(files) - {"manifest.json"}
        checks["payload_hashes"] = checks["complete_manifest"] and all(
            isinstance(digest, str) and hashlib.sha256(files[name]).hexdigest() == digest for name, digest in declared.items()
        )
        checks["trusted_analysis_source"] = files["analysis.py"] == _analysis_source()
        if not all(checks.values()):
            if not checks["trusted_analysis_source"]:
                details.append("Bundled analysis source differs from this trusted checkout. Use the matching reviewed engine version; archive code was not executed.")
            if not checks["payload_hashes"]:
                details.append("Payload hashes or manifest coverage do not match; the archive may have changed.")
            return {"verified": False, "checks": checks, "details": details}
        metadata = json.loads(files["dataset.json"])
        spec = json.loads(files["experiment.json"])
        expected = json.loads(files["result.json"])
        if not all(isinstance(value, dict) for value in [metadata, spec, expected]):
            raise ValueError("Dataset, experiment and result must be JSON objects.")
        if not isinstance(metadata.get("provenance", {}), dict):
            raise ValueError("Dataset provenance must be an object.")
        input_text = files["input.csv"].decode("utf-8")
        reader = csv.DictReader(io.StringIO(input_text))
        if reader.fieldnames != ["timestamp_s", "channel"]:
            raise ValueError("Input CSV schema must be timestamp_s,channel.")
        events = []
        for index, row in enumerate(reader):
            if index >= MAX_EVENTS:
                raise ValueError(f"Normalized input CSV exceeds the {MAX_EVENTS:,}-event verification limit.")
            events.append({"timestamp_s": float(row["timestamp_s"]), "channel": int(row["channel"])})
        checks["input_metadata_hash"] = hashlib.sha256(files["input.csv"]).hexdigest() == metadata.get("evidence_input_sha256")
        if "sha256" in metadata:
            checks["dataset_hash"] = hashlib.sha256(files["input.csv"]).hexdigest() == metadata["sha256"]
        original_hash = metadata.get("provenance", {}).get("original_sha256")
        if original_hash is not None or "original_input.csv" in files:
            checks["original_input_hash"] = "original_input.csv" in files and hashlib.sha256(files["original_input.csv"]).hexdigest() == original_hash
        checks["event_count"] = "event_count" not in metadata or metadata["event_count"] == len(events)
        recomputed = analyze(events, metadata, spec)
        checks["recomputed_result"] = canonical_json(recomputed) == canonical_json(expected)
        if not checks["recomputed_result"]:
            details.append("Recomputed analysis differs from the saved result.")
        if all(checks.values()):
            details.append("Every payload hash matches and the trusted analysis engine reproduces the complete saved result.")
        details.append("Integrity verification does not establish acquisition authenticity or biological learning.")
        return {"verified": all(checks.values()), "checks": checks, "details": details}
    except (ValueError, TypeError, KeyError, UnicodeError, csv.Error, zipfile.BadZipFile, OverflowError, RuntimeError, RecursionError) as exc:
        details.append(str(exc))
        return {"verified": False, "checks": checks, "details": details}

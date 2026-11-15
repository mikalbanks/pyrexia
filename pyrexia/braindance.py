"""Descriptive organoid-level comparisons of published BrainDance run summaries.

Runtime inputs are neutral CSV/JSON. The application never loads a pickle.
This module is stdlib-only so an evidence archive can recompute independently.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile

RESOURCE_DIR = Path(__file__).resolve().parent / "resources"
REQUIRED_COLUMNS = {"experiment_id", "organoid", "chip", "batch", "paradigm", "run_index", "run_name", "start_time", "condition", "top_decile_reward", "episode_count", "mean_episode_reward"}
METHOD_VERSION = "braindance-descriptive-1"


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def parse_trials(raw: bytes) -> list[dict]:
    """Validate the neutral run summary schema (one row per recorded run)."""
    if len(raw) > 2_000_000:
        raise ValueError("BrainDance summary CSV exceeds 2 MB")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if set(reader.fieldnames or []) != REQUIRED_COLUMNS:
            raise ValueError("BrainDance CSV columns do not match the normalized run schema")
        rows, seen = [], set()
        for line, source in enumerate(reader, start=2):
            row = dict(source)
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed BrainDance CSV row {line}")
            for field in ("experiment_id", "organoid", "chip", "run_name"):
                if not row[field].strip():
                    raise ValueError(f"Missing {field} at row {line}")
            if row["condition"] not in {"rl", "random", "none"} or row["paradigm"] not in {"cycled", "continuous"}:
                raise ValueError(f"Unknown condition or paradigm at row {line}")
            row["run_index"] = int(row["run_index"])
            row["episode_count"] = int(row["episode_count"])
            row["batch"] = int(row["batch"]) if row["batch"] else None
            row["top_decile_reward"] = float(row["top_decile_reward"])
            row["mean_episode_reward"] = float(row["mean_episode_reward"]) if row["mean_episode_reward"] else None
            if row["run_index"] < 0 or row["episode_count"] < 0:
                raise ValueError(f"Negative count at row {line}")
            values = [row["top_decile_reward"]] + ([row["mean_episode_reward"]] if row["mean_episode_reward"] is not None else [])
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ValueError(f"Invalid reward at row {line}")
            key = (row["experiment_id"], row["run_index"])
            if key in seen:
                raise ValueError(f"Duplicate experiment/run index at row {line}")
            seen.add(key)
            rows.append(row)
        if not rows:
            raise ValueError("BrainDance summary CSV has no runs")
        return sorted(rows, key=lambda x: (x["organoid"], x["experiment_id"], x["run_index"]))
    except (UnicodeError, TypeError, OverflowError) as exc:
        raise ValueError("Invalid BrainDance summary CSV") from exc


def load_published_trials() -> list[dict]:
    raw = (RESOURCE_DIR / "braindance_runs.csv").read_bytes()
    source = json.loads((RESOURCE_DIR / "braindance_source.json").read_text())
    if hashlib.sha256(raw).hexdigest() != source["normalized_sha256"]:
        raise ValueError("Bundled BrainDance CSV hash does not match its provenance")
    return parse_trials(raw)


def summarize_trials(rows: list[dict], paradigm: str = "cycled") -> dict:
    """Equal weight per organoid; paired contrasts only within selected paradigm.

    Repeated runs are not treated as independent biological replicates. No
    significance test or causal interpretation is added to this secondary view.
    """
    if paradigm not in {"cycled", "continuous", "all"}:
        raise ValueError("paradigm must be cycled, continuous, or all")
    selected = [r for r in rows if paradigm == "all" or r["paradigm"] == paradigm]
    groups: dict[tuple[str, str], list[float]] = {}
    for row in selected:
        value = float(row["top_decile_reward"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("Run rewards must be finite and nonnegative")
        groups.setdefault((row["organoid"], row["condition"]), []).append(value)
    organoids = [
        {"organoid": organoid, "condition": condition, "run_count": len(values), "mean_top_decile_reward": math.fsum(values) / len(values)}
        for (organoid, condition), values in sorted(groups.items())
    ]
    condition_summary = []
    for condition in ("none", "random", "rl"):
        matching = [r for r in organoids if r["condition"] == condition]
        condition_summary.append({
            "condition": condition, "organoid_count": len(matching), "run_count": sum(r["run_count"] for r in matching),
            "mean_organoid_top_decile_reward": math.fsum(r["mean_top_decile_reward"] for r in matching) / len(matching) if matching else None,
        })
    comparisons = []
    lookup = {(r["organoid"], r["condition"]): r["mean_top_decile_reward"] for r in organoids}
    for control in ("none", "random"):
        pairs = []
        for organoid in sorted({r["organoid"] for r in organoids}):
            if (organoid, "rl") in lookup and (organoid, control) in lookup:
                rl, reference = lookup[organoid, "rl"], lookup[organoid, control]
                pairs.append({"organoid": organoid, "rl": rl, "control": reference, "difference": rl - reference})
        differences = [p["difference"] for p in pairs]
        comparisons.append({
            "control": control, "paired_organoid_count": len(pairs),
            "mean_difference": math.fsum(differences) / len(differences) if differences else None,
            "median_difference": statistics.median(differences) if differences else None,
            "positive_organoids": sum(x > 0 for x in differences), "pairs": pairs,
        })
    return {
        "method_version": METHOD_VERSION, "paradigm": paradigm, "total_runs": len(rows), "selected_runs": len(selected),
        "selected_organoids": len({r["organoid"] for r in selected}), "units": "source reward units",
        "condition_summary": condition_summary, "organoids": organoids, "comparisons": comparisons,
        "method": "Average published top_decile within each organoid and condition, then give each organoid equal weight. Paired differences are RL minus each control within the same organoid.",
        "interpretation": "Descriptive secondary analysis; repeated runs, batch, order, and carryover can confound comparisons. No claim of causal learning or full paper reproduction.",
    }


def published_status() -> dict:
    try:
        rows = load_published_trials()
        source = json.loads((RESOURCE_DIR / "braindance_source.json").read_text())
        return {"ready": True, "source": source, "run_count": len(rows), "organoid_count": len({r["organoid"] for r in rows})}
    except (OSError, ValueError, KeyError) as exc:
        return {"ready": False, "error": str(exc)}


def published_report(paradigm: str = "cycled") -> dict:
    rows = load_published_trials()
    return {"source": json.loads((RESOURCE_DIR / "braindance_source.json").read_text()), "summary": summarize_trials(rows, paradigm), "runs": rows}


def export_braindance_evidence(paradigm: str = "cycled") -> bytes:
    report = published_report(paradigm)
    files = {
        "runs.csv": (RESOURCE_DIR / "braindance_runs.csv").read_bytes(),
        "source.json": _json_bytes(report["source"]), "summary.json": _json_bytes(report["summary"]),
        "braindance.py": Path(__file__).read_bytes(),
        "README.md": b"# Published BrainDance secondary analysis\n\nSource: https://doi.org/10.5281/zenodo.17684862 (Robbins et al., 2025), CC-BY-4.0.\n\nPython 3.12+ standard library only. Verify this ZIP with:\n`python braindance.py --verify /path/to/evidence.zip`\n\nRecompute after extraction:\n`python braindance.py --csv runs.csv --paradigm " + paradigm.encode() + b" --output recomputed.json`\n\nCompare recomputed.json with summary.json. source.json describes the exact original hash, extraction, metric units, discrepancies and limitations. runs.csv contains processed run summaries, not raw electrophysiology. Hash checks prove integrity, not recording authenticity. Do not execute Python from an archive you do not trust.\n",
    }
    manifest = {"schema": "pyrexia.braindance.evidence.v1", "paradigm": paradigm, "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for name, raw in sorted(files.items()):
            zip_file.writestr(name, raw)
        zip_file.writestr("manifest.json", _json_bytes(manifest))
    return archive.getvalue()


def verify_braindance_evidence(raw: bytes) -> dict:
    expected = {"runs.csv", "source.json", "summary.json", "braindance.py", "README.md", "manifest.json"}
    if len(raw) > 5_000_000:
        raise ValueError("Evidence ZIP exceeds 5 MB")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if set(names) != expected or len(names) != len(expected) or any(i.file_size > 2_000_000 for i in archive.infolist()):
            raise ValueError("Unexpected, duplicate, or oversized evidence member")
        files = {name: archive.read(name) for name in expected}
    manifest = json.loads(files.pop("manifest.json"))
    if manifest.get("schema") != "pyrexia.braindance.evidence.v1" or set(manifest.get("files", {})) != set(files):
        raise ValueError("Invalid BrainDance evidence manifest")
    if any(hashlib.sha256(content).hexdigest() != manifest["files"][name] for name, content in files.items()):
        raise ValueError("Evidence file hash mismatch")
    if files["braindance.py"] != Path(__file__).read_bytes():
        raise ValueError("BrainDance analysis source version mismatch; use the trusted matching verifier")
    source = json.loads(files["source.json"])
    if hashlib.sha256(files["runs.csv"]).hexdigest() != source["normalized_sha256"]:
        raise ValueError("Normalized source hash mismatch")
    rows = parse_trials(files["runs.csv"])
    recomputed = summarize_trials(rows, manifest["paradigm"])
    if recomputed != json.loads(files["summary.json"]):
        raise ValueError("Recomputed BrainDance summary differs from recorded output")
    return {"verified": True, "checks": ["archive_members", "sha256", "normalized_source", "independent_recompute"], "run_count": len(rows), "method_version": METHOD_VERSION}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--paradigm", choices=["cycled", "continuous", "all"], default="cycled")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify_braindance_evidence(args.verify.read_bytes())
    elif args.csv:
        result = summarize_trials(parse_trials(args.csv.read_bytes()), args.paradigm)
    else:
        parser.error("provide --csv or --verify")
    if args.output:
        args.output.write_bytes(_json_bytes(result))
    else:
        print(_json_bytes(result).decode(), end="")

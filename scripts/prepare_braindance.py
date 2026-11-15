#!/usr/bin/env python3
"""Convert one reviewed, hash-pinned Zenodo artifact to inert CSV summaries.

This is a developer preprocessing tool, never an upload endpoint. It does not
import NumPy or publisher code. Only three reviewed NumPy pickle names are
mapped to local inert representations; all other globals are rejected.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import pickle
import pickletools
import struct
import urllib.request

SOURCE_URL = "https://zenodo.org/records/17684862/files/aggregated_experiment_data.pkl?download=1"
SOURCE_SHA256 = "e84484e116187448dbba1c6860c5970b6ae2bc7a58f20b3a1525d0b5dedb0fd5"
SOURCE_MD5 = "af99f1f859136ca4a6dad47a1aa7c86d"
FIELDS = ["experiment_id", "organoid", "chip", "batch", "paradigm", "run_index", "run_name", "start_time", "condition", "top_decile_reward", "episode_count", "mean_episode_reward"]


class InertDtype:
    def __init__(self, code, *_args):
        if code not in {"i8", "f4"}:
            raise ValueError(f"Unreviewed array dtype: {code}")
        self.code = code
        self.byteorder = "<"

    def __setstate__(self, state):
        if not isinstance(state, tuple) or len(state) != 8 or state[1] not in {"<", ">", "="}:
            raise ValueError("Unreviewed dtype state")
        self.byteorder = ">" if state[1] == ">" else "<"


def discard_array(buffer, dtype, shape, order):
    # Baseline/connectivity arrays are deliberately not reconstructed or used.
    if not isinstance(buffer, (bytes, bytearray)) or not isinstance(dtype, InertDtype):
        raise ValueError("Invalid inert array")
    if not isinstance(shape, tuple) or any(type(n) is not int or n < 0 for n in shape) or order not in {"C", "F"}:
        raise ValueError("Invalid array shape")
    if math.prod(shape) * int(dtype.code[1:]) != len(buffer):
        raise ValueError("Inconsistent array size")
    return None


def numeric_scalar(dtype, data):
    if not isinstance(dtype, InertDtype) or dtype.code != "i8" or not isinstance(data, bytes) or len(data) != 8:
        raise ValueError("Unreviewed scalar")
    return struct.unpack(dtype.byteorder + "q", data)[0]


class InertUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {
            ("numpy", "dtype"): InertDtype,
            ("numpy._core.numeric", "_frombuffer"): discard_array,
            ("numpy._core.multiarray", "scalar"): numeric_scalar,
        }
        if (module, name) not in allowed:
            raise ValueError(f"Pickle global is not allowed: {module}.{name}")
        return allowed[(module, name)]

    def persistent_load(self, _pid):
        raise ValueError("Persistent pickle IDs are disabled")


def load_reviewed_artifact(raw: bytes):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source SHA256 mismatch; only the reviewed Zenodo artifact is supported")
    forbidden = {"EXT1", "EXT2", "EXT4", "PERSID", "BINPERSID", "INST", "OBJ", "NEWOBJ", "NEWOBJ_EX"}
    for op, _arg, _pos in pickletools.genops(raw):
        if op.name in forbidden:
            raise ValueError(f"Forbidden pickle opcode: {op.name}")
    stream = io.BytesIO(raw)
    value = InertUnpickler(stream).load()
    if stream.tell() != len(raw) or not isinstance(value, dict):
        raise ValueError("Unexpected artifact structure")
    return value


def convert(raw: bytes, output: Path):
    data = load_reviewed_artifact(raw)
    rows = []
    for exp_id, experiment in data.items():
        meta = experiment["metadata"]
        for index, run in enumerate(experiment["cartpole"]["runs"]):
            rewards = run.get("reward_log", {}).get("reward", [])
            if not isinstance(rewards, list) or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in rewards):
                raise ValueError(f"Invalid reward log in {exp_id}/{index}")
            top = run.get("top_decile")
            if not isinstance(top, (int, float)) or not math.isfinite(top):
                raise ValueError(f"Invalid published metric in {exp_id}/{index}")
            rows.append(dict(zip(FIELDS, [exp_id, meta["organoid"], meta["chip"], meta.get("batch"), meta["paradigm"], index, run["basename"], run["start_time"], run["exp_type"], float(top), len(rewards), sum(rewards) / len(rewards) if rewards else ""])))
    rows.sort(key=lambda x: (x["organoid"], x["experiment_id"], x["run_index"]))
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "braindance_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    source = {
        "title": "Goal-Directed Learning in Cortical Organoids - Experimental Data and Code",
        "citation": "Robbins, A., et al. (2025). Zenodo, version v2. https://doi.org/10.5281/zenodo.17684862",
        "doi": "10.5281/zenodo.17684862", "url": "https://zenodo.org/records/17684862", "source_url": SOURCE_URL,
        "license": "CC-BY-4.0", "source_kind": "published_biological_recording_summary",
        "source_sha256": SOURCE_SHA256, "source_md5": SOURCE_MD5,
        "normalized_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "source_experiment_count": len(data), "source_organoid_count": len({r["organoid"] for r in rows}), "source_run_count": len(rows),
        "source_episode_count": sum(r["episode_count"] for r in rows),
        "metric": "Published run-level top_decile (mean reward in top 10% of episodes), preserved without reinterpretation.",
        "units": "source reward units; no conversion to seconds",
        "transform": "Retained experiment/organoid metadata and run-level published top_decile; counted reward-log episodes and averaged raw episode rewards. Baseline/causal arrays and game logs omitted.",
        "normalizer": "scripts/prepare_braindance.py; reviewed source hash plus inert restricted pickle decoding; no publisher code or NumPy constructors executed",
        "limitations": [
            "The landing page describes 19 organoids and 432 cycles; the pinned v2 file contains 16 organoid IDs and 426 runs across 38 experiments. Computed file counts are displayed.",
            "The README describes reward as time balanced, while phases.py accumulates environment step rewards. Values are displayed in source reward units, not wall-clock seconds.",
            "This is a descriptive secondary analysis of published processed run summaries. It does not reproduce raw electrophysiology preprocessing, the full paper analysis, or establish causal biological learning.",
            "Repeated runs are aggregated within organoid and condition before comparing organoids. Culture batch, order, training carryover, and unequal run counts can confound comparisons.",
        ],
    }
    (output / "braindance_source.json").write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: source[k] for k in ("normalized_sha256", "source_experiment_count", "source_organoid_count", "source_run_count", "source_episode_count")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, help="Local hash-pinned published pickle")
    parser.add_argument("--download", action="store_true", help="Fetch the single known public Zenodo source")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "pyrexia" / "resources")
    args = parser.parse_args()
    if args.download:
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
            content = response.read(100_000_001)
        if len(content) > 100_000_000:
            raise SystemExit("Published file exceeds the reviewed size limit")
    elif args.source:
        content = args.source.read_bytes()
    else:
        parser.error("provide a local source path or --download")
    convert(content, args.output)

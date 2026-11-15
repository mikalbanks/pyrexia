import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import pickle
import zipfile

import pytest

from pyrexia.braindance import (
    export_braindance_evidence,
    load_published_trials,
    parse_trials,
    published_status,
    summarize_trials,
    verify_braindance_evidence,
)


def run(organoid, condition, reward, index, paradigm="cycled"):
    return {"experiment_id": organoid, "organoid": organoid, "condition": condition, "top_decile_reward": reward, "run_index": index, "paradigm": paradigm}


def test_repeated_runs_do_not_become_biological_replicates():
    rows = [run("A", "rl", 10, i) for i in range(100)]
    rows += [run("A", "none", 5, 100), run("B", "rl", 30, 0), run("B", "none", 10, 1)]
    summary = summarize_trials(rows)
    adaptive = next(c for c in summary["condition_summary"] if c["condition"] == "rl")
    assert adaptive["mean_organoid_top_decile_reward"] == 20
    assert adaptive["organoid_count"] == 2
    paired = summary["comparisons"][0]
    assert paired["paired_organoid_count"] == 2
    assert paired["mean_difference"] == 12.5


def test_default_comparisons_only_use_cycled_with_matched_conditions():
    rows = [run("A", "rl", 10, 0), run("A", "random", 8, 1), run("B", "rl", 100, 0, "continuous")]
    summary = summarize_trials(rows)
    assert summary["total_runs"] == 3
    assert summary["selected_runs"] == 2
    assert summary["comparisons"][0]["paired_organoid_count"] == 0
    assert summary["comparisons"][0]["mean_difference"] is None
    assert summary["comparisons"][1]["mean_difference"] == 2


def test_actual_published_file_counts_and_integrity():
    status = published_status()
    assert status["ready"]
    assert status["organoid_count"] == 16
    rows = load_published_trials()
    assert len(rows) == 426
    assert len({r["experiment_id"] for r in rows}) == 38
    assert sum(r["episode_count"] for r in rows) == status["source"]["source_episode_count"]
    assert status["source"]["source_sha256"] == "e84484e116187448dbba1c6860c5970b6ae2bc7a58f20b3a1525d0b5dedb0fd5"


def test_export_recomputes_and_tamper_fails():
    raw = export_braindance_evidence()
    assert verify_braindance_evidence(raw)["verified"]
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["summary.json"] = b"{}"
    tampered = io.BytesIO()
    with zipfile.ZipFile(tampered, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_braindance_evidence(tampered.getvalue())


def test_changed_analysis_source_is_rejected_even_when_rehashed():
    raw = export_braindance_evidence()
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        files = {name: source.read(name) for name in source.namelist()}
    files["braindance.py"] += b"\n# changed analysis version\n"
    manifest = json.loads(files["manifest.json"])
    manifest["files"]["braindance.py"] = hashlib.sha256(files["braindance.py"]).hexdigest()
    files["manifest.json"] = json.dumps(manifest).encode()
    changed = io.BytesIO()
    with zipfile.ZipFile(changed, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match="source version mismatch"):
        verify_braindance_evidence(changed.getvalue())


def test_csv_rejects_nan_and_duplicates():
    csv_path = Path(__file__).resolve().parents[1] / "pyrexia/resources/braindance_runs.csv"
    reader = csv.DictReader(io.StringIO(csv_path.read_text()))
    row = next(reader)
    raw = io.StringIO()
    writer = csv.DictWriter(raw, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerow({**row, "top_decile_reward": "nan"})
    with pytest.raises(ValueError, match="Invalid reward"):
        parse_trials(raw.getvalue().encode())
    raw = io.StringIO()
    writer = csv.DictWriter(raw, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows([row, row])
    with pytest.raises(ValueError, match="Duplicate"):
        parse_trials(raw.getvalue().encode())


def test_preprocessor_rejects_other_pickle_globals_and_unpinned_sources():
    path = Path(__file__).resolve().parents[1] / "scripts/prepare_braindance.py"
    spec = importlib.util.spec_from_file_location("prepare_braindance", path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    # A harmless eval result demonstrates that callable globals are rejected.
    class Unreviewed:
        def __reduce__(self):
            return eval, ("1+1",)
    with pytest.raises(ValueError, match="not allowed"):
        converter.InertUnpickler(io.BytesIO(pickle.dumps(Unreviewed()))).load()
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        converter.load_reviewed_artifact(pickle.dumps({"arbitrary": "file"}))

import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from pyrexia.analysis import analyze
from pyrexia.evidence import canonical_json, events_csv, export_evidence, verify_evidence


def repack(payload, changed, rehash=False):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files.update(changed)
    if rehash:
        manifest = json.loads(files["manifest.json"])
        manifest["files"] = {name: hashlib.sha256(content).hexdigest() for name, content in files.items() if name != "manifest.json"}
        files["manifest.json"] = canonical_json(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        events = [{"timestamp_s": 0.1, "channel": 0}, {"timestamp_s": 1.0, "channel": 1}]
        self.dataset = {"id": "sample", "name": "Synthetic", "duration_s": 2, "n_channels": 2, "event_count": 2, "source_kind": "synthetic", "events": events, "provenance": {"seed": 42}, "sha256": hashlib.sha256(events_csv(events)).hexdigest()}
        self.spec = {"recipe": "signal_stability", "bin_s": 1}
        self.result = analyze(events, self.dataset, self.spec)
        self.payload = export_evidence(self.dataset, self.spec, self.result, {"id": "run1", "created_at": "2026-11-15T00:00:00Z"})

    def test_full_recomputation_and_independent_cli(self):
        verification = verify_evidence(self.payload)
        self.assertTrue(verification["verified"], verification)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.zip"
            path.write_bytes(self.payload)
            command = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "verify_evidence.py"), str(path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(command.returncode, 0, command.stdout + command.stderr)
        self.assertTrue(json.loads(command.stdout)["checks"]["recomputed_result"])

    def test_tampered_input_rejected_by_hash(self):
        verification = verify_evidence(repack(self.payload, {"input.csv": b"timestamp_s,channel\n0.2,0\n1.0,1\n"}))
        self.assertFalse(verification["verified"])
        self.assertFalse(verification["checks"]["payload_hashes"])

    def test_changed_result_rejected_even_if_manifest_rehashed(self):
        result = dict(self.result, metrics={**self.result["metrics"], "event_count": 100})
        verification = verify_evidence(repack(self.payload, {"result.json": canonical_json(result)}, rehash=True))
        self.assertFalse(verification["verified"])
        self.assertTrue(verification["checks"]["payload_hashes"])
        self.assertFalse(verification["checks"]["recomputed_result"])

    def test_changed_bundled_engine_never_executed(self):
        malicious_source = b"raise RuntimeError('THIS MUST NEVER EXECUTE')\n"
        verification = verify_evidence(repack(self.payload, {"analysis.py": malicious_source}, rehash=True))
        self.assertFalse(verification["verified"])
        self.assertFalse(verification["checks"]["trusted_analysis_source"])

    def test_unmanifested_files_and_unsafe_paths_rejected(self):
        for name in ["extra.txt", "../outside.txt", "/absolute.txt", "folder\\evil.txt"]:
            with self.subTest(name=name):
                verification = verify_evidence(repack(self.payload, {name: b"unexpected"}))
                self.assertFalse(verification["verified"])
        self.assertFalse(verify_evidence(repack(self.payload, {"extra.txt": b"unexpected"}, rehash=True))["verified"])

    def test_original_upload_preserved_and_checked(self):
        original = b"timestamp_s,channel\n1,1\n0.1,0\n"
        dataset = {**self.dataset, "original_filename": "recording.csv", "original_input_base64": base64.b64encode(original).decode(), "provenance": {"original_sha256": hashlib.sha256(original).hexdigest()}}
        payload = export_evidence(dataset, self.spec, self.result, {})
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(archive.read("original_input.csv"), original)
            self.assertNotIn("original_input_base64", json.loads(archive.read("dataset.json")))
        verification = verify_evidence(payload)
        self.assertTrue(verification["verified"], verification)
        self.assertTrue(verification["checks"]["original_input_hash"])

    def test_missing_original_or_bad_metadata_hash_fails(self):
        dataset_metadata = {key: value for key, value in self.dataset.items() if key != "events"}
        dataset_metadata.update({"evidence_input_sha256": "incorrect", "provenance": {"original_sha256": "abc"}})
        verification = verify_evidence(repack(self.payload, {"dataset.json": canonical_json(dataset_metadata)}, rehash=True))
        self.assertFalse(verification["verified"])
        self.assertFalse(verification["checks"]["input_metadata_hash"])
        self.assertFalse(verification["checks"]["original_input_hash"])

    def test_invalid_zip_returns_failure_without_exception(self):
        self.assertFalse(verify_evidence(b"not a zip")["verified"])
        self.assertFalse(verify_evidence(repack(self.payload, {"manifest.json": b"[]"}))["verified"])

    def test_normalized_input_size_and_event_count_are_bounded(self):
        with patch("pyrexia.evidence.MAX_EVENTS", 1):
            verification = verify_evidence(self.payload)
        self.assertFalse(verification["verified"])
        self.assertTrue(any("event verification limit" in detail for detail in verification["details"]))
        with patch("pyrexia.evidence.MAX_INPUT_BYTES", 1):
            verification = verify_evidence(self.payload)
        self.assertFalse(verification["verified"])
        self.assertTrue(any("CSV exceeds" in detail for detail in verification["details"]))


if __name__ == "__main__":
    unittest.main()

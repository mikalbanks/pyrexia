from datetime import datetime, timezone
import importlib.metadata
import sys
from types import SimpleNamespace

import pytest

from pyrexia import _cortical_worker
from pyrexia.providers import (
    FinalSparkReadOnlyAdapter,
    cortical_dataset,
    fixture_dataset,
    provider_status,
    synthetic_dataset,
)


def test_synthetic_reproducible_and_explicit_silent_duration():
    config = {"seed": 42, "duration_s": 8, "n_channels": 4}
    first = synthetic_dataset(config)
    assert first == synthetic_dataset(config)
    events, metadata = first
    assert events == sorted(events, key=lambda event: (event["timestamp_s"], event["channel"]))
    assert metadata["stimuli_s"] == [1.0, 4.0, 7.0]
    assert all(0 <= event["timestamp_s"] < 8 and 0 <= event["channel"] < 4 for event in events)
    empty, quiet = synthetic_dataset({"duration_s": 8, "baseline_hz": 0, "response_hz": 0})
    assert empty == []
    assert quiet["duration_s"] == 8
    assert quiet["provenance"]["biological_evidence"] is False


@pytest.mark.parametrize("config", [
    {"duration_s": float("nan")}, {"seed": True}, {"n_channels": 2.5},
    {"duration_s": 300, "n_channels": 64, "baseline_hz": 200},
])
def test_generation_rejects_invalid_or_excessive_requests(config):
    with pytest.raises(ValueError):
        synthetic_dataset(config)


def test_export_uses_explicit_utc_recording_start_and_preserves_channel():
    events, metadata = FinalSparkReadOnlyAdapter().normalize(
        [{"Time": "2026-01-01T01:00:00.250+01:00", "channel": "3"}],
        recording_start="2026-01-01T00:00:00Z", duration_s=10, n_channels=4,
    )
    assert events == [{"timestamp_s": 0.25, "channel": 3}]
    assert metadata["duration_s"] == 10
    assert metadata["provenance"]["network_session"] is False
    assert "authenticat" in metadata["provenance"]["limitations"][0]


@pytest.mark.parametrize("time,channel", [
    ("2026-01-01T00:00:00", 0),  # No timezone
    (1767225600, 0),  # Numeric epoch units must not be guessed
    ("2026-01-01T00:00:10Z", 0),  # End-exclusive recording window
    ("2025-12-31T23:59:59Z", 0),
    ("2026-01-01T00:00:01Z", 4),
])
def test_export_rejects_ambiguous_or_out_of_range_rows(time, channel):
    with pytest.raises(ValueError):
        FinalSparkReadOnlyAdapter().normalize(
            [{"Time": time, "channel": channel}],
            recording_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            duration_s=10, n_channels=4,
        )


@pytest.mark.parametrize("kind", ["finalspark", "braindance"])
def test_fixtures_never_impersonate_provider_recordings(kind):
    events, metadata = fixture_dataset(kind)
    assert events
    assert metadata["source_kind"] == "test_fixture"
    assert "synthetic" in metadata["name"]
    assert metadata["provenance"]["biological_evidence"] is False
    assert metadata["provenance"]["mode"] == "test_fixture"
    assert metadata["provenance"]["user_assertions"] == []


def test_hardware_guard_refuses_before_open(monkeypatch):
    opened = []
    fake_cl = SimpleNamespace(is_simulator=lambda: False, open=lambda: opened.append(True))
    monkeypatch.setitem(sys.modules, "cl", fake_cl)
    monkeypatch.setattr(importlib.metadata, "version", lambda _: "1.0.0")
    monkeypatch.setattr(sys, "argv", ["worker", "0.1", "42"])
    with pytest.raises(ValueError, match="Refused CL connection"):
        _cortical_worker.main()
    assert opened == []


def test_missing_sdk_is_explicit_and_status_stays_offline(monkeypatch):
    monkeypatch.setattr("pyrexia.providers._sdk_version", lambda: None)
    with pytest.raises(ValueError, match="Optional simulator requires"):
        cortical_dataset({})
    statuses = {provider["id"]: provider for provider in provider_status()}
    assert statuses["cortical"]["status"] == "optional_dependency"
    assert statuses["finalspark_live"]["status"] == "access_required"
    assert FinalSparkReadOnlyAdapter.readiness()["authorized_live_session"] is False


@pytest.mark.skipif(
    not any(distribution.metadata["Name"] == "cl-sdk" for distribution in importlib.metadata.distributions()),
    reason="optional cl-sdk research dependency is not installed",
)
def test_actual_cortical_simulator_acquires_and_is_reproducible(monkeypatch):
    # A user's replay/custom-source settings must not turn this acquisition into
    # a file import or a network-backed simulator data source.
    monkeypatch.setenv("CL_SDK_DATA_SOURCE", "not_a_real_package:network_source")
    monkeypatch.setenv("CL_SDK_REPLAY_PATH", "/does-not-exist/recording.h5")
    monkeypatch.setenv("CL_SDK_REPLAY_START_OFFSET", "123456")
    first_events, first_metadata = cortical_dataset({"duration_s": 0.2, "seed": 42})
    second_events, second_metadata = cortical_dataset({"duration_s": 0.2, "seed": 42})
    assert first_events == second_events
    assert first_metadata == second_metadata
    assert first_events
    assert all(0 <= event["timestamp_s"] < 0.2 for event in first_events)
    assert first_metadata["n_channels"] == 64
    assert first_metadata["provenance"]["simulator_verified"] is True
    assert first_metadata["provenance"]["biological_evidence"] is False

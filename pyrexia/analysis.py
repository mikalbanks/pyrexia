"""Deterministic descriptive analysis of timestamped extracellular spike events.

This module deliberately uses only Python's standard library so evidence bundles
can be recomputed without a provider SDK, network access, or notebook state.
"""

from __future__ import annotations

import math
import statistics
from bisect import bisect_left, bisect_right
from decimal import Decimal, ROUND_CEILING
from typing import Any

ENGINE_VERSION = "0.5.0"
MAX_PLOT_EVENTS = 10_000
MAX_BINS = 10_000


def _positive(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite positive number.") from exc
    if isinstance(value, bool) or not math.isfinite(number) or not 1e-9 <= number <= 1e9:
        raise ValueError(f"{name} must be a finite number between 1e-9 and 1e9 seconds.")
    return number


def normalized_events(events: list[dict], duration_s: float, n_channels: int) -> list[dict]:
    """Validate, canonicalize and sort while preserving coincident spike events."""
    result = []
    for index, event in enumerate(events):
        try:
            timestamp = float(event["timestamp_s"])
            raw_channel = event["channel"]
            channel_number = float(raw_channel)
        except (TypeError, KeyError, ValueError, OverflowError) as exc:
            raise ValueError(f"Event {index + 1} needs numeric timestamp_s and integer channel.") from exc
        if isinstance(event["timestamp_s"], bool) or not math.isfinite(timestamp) or not 0 <= timestamp < duration_s:
            raise ValueError(f"Event {index + 1}: timestamp_s must be within [0, duration_s).")
        if isinstance(raw_channel, bool) or not math.isfinite(channel_number) or not channel_number.is_integer():
            raise ValueError(f"Event {index + 1}: channel must be an integer.")
        channel = int(channel_number)
        if not 0 <= channel < n_channels:
            raise ValueError(f"Event {index + 1}: channel must be within 0 through {n_channels - 1}.")
        result.append({"timestamp_s": timestamp, "channel": channel})
    result.sort(key=lambda event: (event["timestamp_s"], event["channel"]))
    return result


def analyze(events: list[dict], metadata: dict, spec: dict) -> dict:
    """Compute descriptive population statistics, never learning or efficacy claims.

    Rates are events per second per configured recording channel. All windows
    are half-open, and the final partial bin uses its actual duration.
    """
    duration = _positive(metadata.get("duration_s"), "duration_s")
    raw_channels = metadata.get("n_channels")
    try:
        channels = int(raw_channels)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("n_channels must be an integer from 1 to 4096.") from exc
    if isinstance(raw_channels, bool) or channels != raw_channels or not 1 <= channels <= 4096:
        raise ValueError("n_channels must be an integer from 1 to 4096.")
    recipe = spec.get("recipe")
    if recipe not in {"stimulus_response", "signal_stability"}:
        raise ValueError("Choose the stimulus_response or signal_stability recipe.")
    bin_s = _positive(spec.get("bin_s", 1.0), "bin_s")
    decimal_duration, decimal_bin = Decimal(str(duration)), Decimal(str(bin_s))
    bin_count = int((decimal_duration / decimal_bin).to_integral_value(rounding=ROUND_CEILING))
    if bin_count > MAX_BINS:
        raise ValueError(f"Choose bin_s so the recording contains at most {MAX_BINS} bins.")
    # Construct decimal time edges before converting to floats. int(t / width)
    # puts literal 0.3 in bin 2 for width 0.1 due to binary division rounding.
    # Exact comparisons against canonical decimal edges retain the half-open
    # policy, even for the representable float immediately before a boundary.
    decimal_edges = [min(decimal_duration, index * decimal_bin) for index in range(bin_count + 1)]
    edges = [float(edge) for edge in decimal_edges]
    canonical = normalized_events(events, duration, channels)
    times = [event["timestamp_s"] for event in canonical]
    counts = [0] * bin_count
    channel_counts = [0] * channels
    for event in canonical:
        counts[min(bisect_right(edges, event["timestamp_s"]) - 1, bin_count - 1)] += 1
        channel_counts[event["channel"]] += 1
    exposures = [float(end - start) for start, end in zip(decimal_edges, decimal_edges[1:])]
    bin_rates = [count / (exposure * channels) for count, exposure in zip(counts, exposures)]
    channel_rates = [count / duration for count in channel_counts]
    warnings = [
        "Descriptive signal statistics do not establish biological learning, causation, clinical benefit, or computing advantage."
    ]
    source_kind = str(metadata.get("source_kind", "unknown"))
    if "synthetic" in source_kind or "simulat" in source_kind or "fixture" in source_kind:
        warnings.append("This dataset is synthetic, simulated, or a test fixture; it is not evidence from living neurons.")
    if len(canonical) < 20:
        warnings.append("Fewer than 20 events: descriptive estimates may be unstable; no statistical significance is inferred.")
    if len(canonical) > MAX_PLOT_EVENTS:
        warnings.append(f"The raster displays the first {MAX_PLOT_EVENTS} events; all events are included in computed metrics.")
    duplicate_count = sum(a == b for a, b in zip(canonical, canonical[1:]))
    if duplicate_count:
        warnings.append(f"{duplicate_count} repeated timestamp/channel records were retained; inspect source acquisition for duplicate events.")
    metrics = {
        "event_count": len(canonical),
        "duration_s": duration,
        "recording_channels": channels,
        "active_channels": sum(count > 0 for count in channel_counts),
        "mean_rate_hz_per_channel": len(canonical) / (duration * channels),
    }
    method = {
        "engine_version": ENGINE_VERSION,
        "time_unit": "seconds",
        "channel_indexing": "zero-based",
        "rate_unit": "events/s/configured channel (Hz/channel)",
        "channel_denominator": channels,
        "window_policy": "half-open [start, stop), with boundaries constructed from decimal time representations; events at duration_s excluded by validation",
        "bin_s": bin_s,
        "bin_boundary_policy": "Half-open edges constructed from decimal time representations; no tolerance snapping.",
        "bin_exposures_s": exposures,
        "raster_events_displayed": min(len(canonical), MAX_PLOT_EVENTS),
        "inference": "descriptive only; no significance, learning, energy, or platform equivalence claim",
    }
    plots = {
        "raster": {"x": times[:MAX_PLOT_EVENTS], "y": [event["channel"] for event in canonical[:MAX_PLOT_EVENTS]]},
        "firing_rate": {"x": [float((start + end) / 2) for start, end in zip(decimal_edges, decimal_edges[1:])], "y": bin_rates},
        "channels": {"x": list(range(channels)), "y": channel_rates},
    }
    if recipe == "signal_stability":
        midpoint = duration / 2
        early_count = bisect_left(times, midpoint)
        early_rate = early_count / (midpoint * channels)
        late_rate = (len(times) - early_count) / (midpoint * channels)
        # Weighted population dispersion across bins, since the final bin may
        # expose less time than the others. This is not an uncertainty interval.
        mean_rate = metrics["mean_rate_hz_per_channel"]
        variance = sum(exposure * (rate - mean_rate) ** 2 for rate, exposure in zip(bin_rates, exposures)) / duration
        metrics.update({
            "first_half_rate_hz_per_channel": early_rate,
            "second_half_rate_hz_per_channel": late_rate,
            "second_minus_first_rate_hz_per_channel": late_rate - early_rate,
            "second_to_first_rate_ratio": late_rate / early_rate if early_rate else None,
            "time_weighted_bin_rate_cv": math.sqrt(variance) / mean_rate if mean_rate else None,
            "bin_count": bin_count,
        })
        method["stability_method"] = "Compare equal-duration recording halves; report time-weighted population CV across rate bins. CV is undefined for zero total events."
        if bin_count < 2:
            warnings.append("Only one time bin: the binned CV cannot describe variation over time.")
    else:
        baseline_window = _positive(spec.get("baseline_window_s", 0.2), "baseline_window_s")
        response_window = _positive(spec.get("response_window_s", 0.2), "response_window_s")
        decimal_baseline = Decimal(str(baseline_window))
        decimal_response = Decimal(str(response_window))
        raw_stimuli = metadata.get("stimuli_s", [])
        if not isinstance(raw_stimuli, list) or not raw_stimuli:
            raise ValueError("Stimulus-response analysis requires a nonempty stimuli_s list in dataset metadata.")
        stimuli = []
        for raw_stimulus in raw_stimuli:
            try:
                stimulus = float(raw_stimulus)
            except (TypeError, ValueError) as exc:
                raise ValueError("stimuli_s must contain finite numeric times.") from exc
            if isinstance(raw_stimulus, bool) or not math.isfinite(stimulus):
                raise ValueError("stimuli_s must contain finite numeric times.")
            decimal_stimulus = Decimal(str(stimulus))
            if decimal_stimulus - decimal_baseline < 0 or decimal_stimulus + decimal_response > decimal_duration:
                raise ValueError("Every stimulus must have complete baseline and response windows inside the recording.")
            stimuli.append(stimulus)
        stimuli.sort()
        trial_intervals = [(Decimal(str(stimulus)) - decimal_baseline, Decimal(str(stimulus)) + decimal_response) for stimulus in stimuli]
        # A trial occupies [stimulus-baseline, stimulus+response). Reject any
        # overlap, which would reuse events across baseline/response conditions.
        for previous, current in zip(trial_intervals, trial_intervals[1:]):
            if current[0] < previous[1]:
                raise ValueError("Stimulus baseline/response windows overlap. Reduce windows or supply separated stimuli.")
        baseline_counts, response_counts = [], []
        for stimulus, (start, stop) in zip(stimuli, trial_intervals):
            split = bisect_left(times, stimulus)
            baseline_counts.append(split - bisect_left(times, float(start)))
            response_counts.append(bisect_left(times, float(stop)) - split)
        trial_count = len(stimuli)
        baseline_exposure = float(trial_count * decimal_baseline)
        response_exposure = float(trial_count * decimal_response)
        baseline_rate = sum(baseline_counts) / (baseline_exposure * channels)
        response_rate = sum(response_counts) / (response_exposure * channels)
        deltas = [response / (response_window * channels) - baseline / (baseline_window * channels) for response, baseline in zip(response_counts, baseline_counts)]
        metrics.update({
            "trial_count": trial_count,
            "baseline_event_count": sum(baseline_counts),
            "response_event_count": sum(response_counts),
            "baseline_rate_hz_per_channel": baseline_rate,
            "response_rate_hz_per_channel": response_rate,
            "response_minus_baseline_hz_per_channel": response_rate - baseline_rate,
            "response_to_baseline_rate_ratio": response_rate / baseline_rate if baseline_rate else None,
            "trial_delta_population_sd_hz_per_channel": statistics.pstdev(deltas),
        })
        method.update({
            "baseline_window_s": baseline_window,
            "response_window_s": response_window,
            "baseline_total_exposure_s": baseline_exposure,
            "response_total_exposure_s": response_exposure,
            "stimuli_s": stimuli,
            "response_method": "Pooled condition counts / (condition exposure seconds × configured channels); per-trial changes are descriptive.",
        })
        plots["trial_response"] = {"x": list(range(1, trial_count + 1)), "y": deltas}
        if trial_count < 5:
            warnings.append("Fewer than five trials: report descriptive trial differences only.")
        if not baseline_rate:
            warnings.append("Baseline rate is zero; the response/baseline ratio is undefined (null).")
    return {"recipe": recipe, "metrics": metrics, "warnings": warnings, "plots": plots, "method": method}

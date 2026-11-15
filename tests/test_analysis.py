import json
import math
import unittest

from pyrexia.analysis import analyze


def event(time, channel=0):
    return {"timestamp_s": time, "channel": channel}


class AnalysisTests(unittest.TestCase):
    def test_partial_bin_and_silent_channels_use_actual_exposure(self):
        result = analyze([event(0.1), event(1.1), event(2.1)], {"duration_s": 2.5, "n_channels": 2}, {"recipe": "signal_stability", "bin_s": 1})
        self.assertEqual(result["plots"]["firing_rate"]["y"], [0.5, 0.5, 1.0])
        self.assertEqual(result["plots"]["channels"], {"x": [0, 1], "y": [1.2, 0.0]})
        self.assertEqual(result["metrics"]["mean_rate_hz_per_channel"], 0.6)
        self.assertAlmostEqual(result["metrics"]["time_weighted_bin_rate_cv"], 1 / 3)

    def test_response_pooled_exposure_and_boundary_assignment(self):
        # Stimulus at 1.0: baseline [0.5,1), response [1,1.25).
        # Stimulus at 3.0: baseline [2.5,3), response [3,3.25).
        events = [event(t) for t in [0.49, 0.5, 0.99, 1.0, 1.24, 1.25, 2.5, 3.0]]
        result = analyze(events, {"duration_s": 4, "n_channels": 2, "stimuli_s": [3, 1]}, {"recipe": "stimulus_response", "baseline_window_s": 0.5, "response_window_s": 0.25})
        self.assertEqual(result["metrics"]["baseline_event_count"], 3)
        self.assertEqual(result["metrics"]["response_event_count"], 3)
        self.assertEqual(result["metrics"]["baseline_rate_hz_per_channel"], 1.5)
        self.assertEqual(result["metrics"]["response_rate_hz_per_channel"], 3.0)
        self.assertEqual(result["metrics"]["response_to_baseline_rate_ratio"], 2.0)

    def test_stability_half_boundary_goes_to_late_half(self):
        result = analyze([event(0), event(1), event(1.9)], {"duration_s": 2, "n_channels": 1}, {"recipe": "signal_stability"})
        self.assertEqual(result["metrics"]["first_half_rate_hz_per_channel"], 1)
        self.assertEqual(result["metrics"]["second_half_rate_hz_per_channel"], 2)

    def test_response_decimal_window_edges_preserve_preceding_float(self):
        events = [event(math.nextafter(0.4, -math.inf)), event(0.4), event(math.nextafter(0.6, -math.inf)), event(0.6), event(math.nextafter(0.8, -math.inf)), event(0.8)]
        result = analyze(events, {"duration_s": 1, "n_channels": 1, "stimuli_s": [0.6]}, {"recipe": "stimulus_response", "baseline_window_s": 0.2, "response_window_s": 0.2})
        self.assertEqual(result["metrics"]["baseline_event_count"], 2)
        self.assertEqual(result["metrics"]["response_event_count"], 2)

    def test_adjacent_decimal_trials_are_nonoverlapping(self):
        result = analyze([event(0.3), event(0.5), event(0.7)], {"duration_s": 1, "n_channels": 1, "stimuli_s": [0.3, 0.7]}, {"recipe": "stimulus_response", "baseline_window_s": 0.2, "response_window_s": 0.2})
        self.assertEqual(result["metrics"]["baseline_event_count"], 1)
        self.assertEqual(result["metrics"]["response_event_count"], 2)

    def test_no_events_has_finite_json_and_undefined_ratios(self):
        for recipe in ["signal_stability", "stimulus_response"]:
            result = analyze([], {"duration_s": 2, "n_channels": 2, "stimuli_s": [1]}, {"recipe": recipe})
            json.dumps(result, allow_nan=False)
            self.assertEqual(result["metrics"]["mean_rate_hz_per_channel"], 0)
            self.assertEqual(result["metrics"]["active_channels"], 0)
            self.assertTrue(any(value is None for value in result["metrics"].values()))

    def test_decimal_width_does_not_create_zero_exposure_bin(self):
        result = analyze([event(0.065)], {"duration_s": 0.07, "n_channels": 1}, {"recipe": "signal_stability", "bin_s": 0.01})
        self.assertTrue(all(exposure > 0 for exposure in result["method"]["bin_exposures_s"]))
        self.assertEqual(result["metrics"]["bin_count"], 7)

    def test_decimal_boundary_and_immediately_preceding_float_are_distinct(self):
        metadata = {"duration_s": 0.5, "n_channels": 1}
        spec = {"recipe": "signal_stability", "bin_s": 0.1}
        result = analyze([event(0.2), event(0.3)], metadata, spec)
        self.assertEqual(result["plots"]["firing_rate"]["y"], [0, 0, 10, 10, 0])
        self.assertAlmostEqual(result["metrics"]["time_weighted_bin_rate_cv"], math.sqrt(1.5))
        before = analyze([event(math.nextafter(0.3, -math.inf)), event(0.3)], metadata, spec)
        self.assertEqual(before["plots"]["firing_rate"]["y"], [0, 0, 10, 10, 0])
        before_first = analyze([event(math.nextafter(0.1, -math.inf)), event(0.1)], metadata, spec)
        self.assertEqual(before_first["plots"]["firing_rate"]["y"], [10, 10, 0, 0, 0])

    def test_invalid_events_rejected(self):
        for events in [[event(-0.1)], [event(2)], [event(math.nan)], [event(1, -1)], [event(1, 2)], [event(1, 0.5)], [event(True)], [event(1, True)]]:
            with self.subTest(events=events), self.assertRaises(ValueError):
                analyze(events, {"duration_s": 2, "n_channels": 2}, {"recipe": "signal_stability"})

    def test_invalid_parameters_rejected(self):
        for duration, channels, bin_s in [(0, 2, 1), (1, 0, 1), (1, 1.5, 1), (1, 1, 0), (1, 1, math.inf), (1, 1, 0.000001)]:
            with self.subTest(duration=duration, channels=channels, bin_s=bin_s), self.assertRaises(ValueError):
                analyze([], {"duration_s": duration, "n_channels": channels}, {"recipe": "signal_stability", "bin_s": bin_s})

    def test_overlapping_or_incomplete_stimulus_windows_rejected(self):
        for stimuli in [[0.1], [1.9], [1, 1.1], [1, 1], [], [math.nan]]:
            with self.subTest(stimuli=stimuli), self.assertRaises(ValueError):
                analyze([], {"duration_s": 2, "n_channels": 2, "stimuli_s": stimuli}, {"recipe": "stimulus_response"})

    def test_sorted_and_unsorted_input_give_same_result(self):
        metadata = {"duration_s": 2, "n_channels": 2, "source_kind": "synthetic"}
        spec = {"recipe": "signal_stability"}
        events = [event(0.2, 1), event(1.0, 0), event(1.0, 1)]
        self.assertEqual(analyze(events, metadata, spec), analyze(list(reversed(events)), metadata, spec))


if __name__ == "__main__":
    unittest.main()

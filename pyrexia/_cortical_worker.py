"""Isolated worker for the pinned official CL SDK random simulator.

Called by providers.cortical_dataset in a clean temporary directory. Never open
a CL connection until the documented is_simulator() guard has returned True.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> None:
    duration = float(sys.argv[1])
    seed = int(sys.argv[2])
    # Also clear settings inside the worker; do not load .env or replay/custom
    # data sources that could have network or hardware-backed implementations.
    for key in list(os.environ):
        if key.startswith("CL_"):
            del os.environ[key]
    os.environ.update(CL_SDK_VISUALISATION="0", CL_SDK_WEBSOCKET="0",
                      CL_SDK_ACCELERATED_TIME="1", CL_SDK_RANDOM_SEED=str(seed),
                      CL_SDK_REPLAY_START_OFFSET="0",
                      PYTHON_DOTENV_DISABLED="1")
    import cl
    from importlib.metadata import version

    if version("cl-sdk") != "1.0.0":
        raise ValueError("Only the reviewed cl-sdk==1.0.0 simulator is supported.")
    if not callable(getattr(cl, "is_simulator", None)) or cl.is_simulator() is not True:
        raise ValueError("Refused CL connection: the installed API did not confirm simulator mode.")
    if not hasattr(cl, "sim") or not callable(getattr(cl.sim, "clear_simulator_data_source", None)):
        raise ValueError("Refused CL connection: simulator random-source controls unavailable.")
    cl.sim.clear_simulator_data_source()
    events = []
    with cl.open() as neurons:
        fps = int(neurons.get_frames_per_second())
        channels = int(neurons.get_channel_count())
        start = int(neurons.timestamp())
        for tick in neurons.loop(ticks_per_second=100, stop_after_seconds=duration):
            for spike in tick.analysis.spikes:
                timestamp = (int(spike.timestamp) - start) / fps
                if 0 <= timestamp < duration:
                    events.append({"timestamp_s": timestamp, "channel": int(spike.channel)})
            if len(events) > 250_000:
                raise ValueError("SDK simulator exceeded the event limit.")
    events.sort(key=lambda event: (event["timestamp_s"], event["channel"]))
    Path("result.json").write_text(json.dumps({"events": events, "n_channels": channels,
                                             "frames_per_second": fps}), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if isinstance(exc, ValueError):
            message = str(exc)
        else:
            message = f"Cortical SDK simulator failed ({type(exc).__name__}); check optional dependency compatibility."
        Path("error.json").write_text(json.dumps({"error": message}), encoding="utf-8")
        sys.exit(1)

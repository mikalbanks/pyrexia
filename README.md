# Pyrexia Lab

**Where biology becomes computing.** A working research workstation for configuring experiments, analyzing neural spike recordings, comparing results, and exporting reproducible evidence.

Pyrexia Lab is intended for an academic software demonstration, including a discussion with Georgia Tech or Emory researchers. It does not imply affiliation, endorsement, a research partnership, or validation by either institution.

## What is included

| Module | Working capability |
| --- | --- |
| **Connect** | Seeded synthetic recordings, authorized CSV uploads, optional official Cortical Labs SDK simulator acquisition, and a FinalSpark offline-export normalization adapter with explicitly generated fixtures |
| **Studio** | Platform-independent experiment specifications, stimulus-response and signal-stability recipes, recording metadata, research notes, and persistent run history |
| **Intelligence** | Spike rasters, firing-rate and channel activity plots, descriptive measurements, run comparisons, and secondary analysis of published BrainDance run summaries |
| **Evidence** | Input data, parameters, results, analysis source, environment metadata, SHA-256 manifests, ZIP export, and independent recomputation using trusted project code |

The objective planner suggests a recipe using rules. It is not an LLM or a scientific reviewer. Live CL1 and FinalSpark laboratory sessions are not implemented. Generated data, SDK simulation, published summaries, fixtures, and user-supplied recordings retain distinct provenance.

## Run locally

Use **Python 3.12**. From the extracted project directory:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m uvicorn pyrexia.app:app --host 127.0.0.1 --port 3000
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), then choose **Run guided demo**. API documentation is at [http://127.0.0.1:3000/api/docs](http://127.0.0.1:3000/api/docs).

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\python.exe` for the Python commands above.

### Optional Cortical Labs research simulator

```bash
.venv/bin/python -m pip install -e '.[cortical]'
```

Restart the app, open **Connect**, and acquire a short SDK simulation. This uses the real `cl-sdk==1.0.0` package in an isolated, bounded subprocess. The adapter refuses to open a source unless `cl.is_simulator()` returns `True`.

The SDK is licensed **CC BY-NC 4.0**. This optional integration is for the research/demo workflow; commercial use requires a license review or suitable permission from Cortical Labs. Pyrexia's independently implemented synthetic engine works without it. The default SDK simulator does not learn or respond biologically to stimulation.

## Replit handoff

Import [mikalbanks/pyrexia](https://github.com/mikalbanks/pyrexia) into a Python 3.12 Replit project, or upload and extract the supplied source ZIP. The repository includes `.replit` and `scripts/start.sh`; **Run** starts the single-process application on port 3000.

Paste [the complete Replit prompt](docs/REPLIT_PROMPT.md) into Replit Agent. It asks the agent to run and validate this implementation, complete the specified demonstration checks, and return a working preview and evidence files. The prompt itself does not create a Replit deployment.

For a hosted demonstration, set `PYREXIA_DEMO_PASSWORD` in **Replit Secrets** to at least 12 characters. The login username is `pyrexia`. The app refuses a detected Replit deployment without that password. Keep any deployment private until its audience and storage behavior are checked. No paid upgrade is required by this source code; hosting plan availability is a separate Replit constraint.

## Import a recording

Use a UTF-8 CSV with these columns:

```csv
timestamp_s,channel
0.125,0
0.310,2
1.400,0
```

Supply the actual observation duration and total recorded channel count, including silent channels. Times are in seconds, channels are zero-based, and timestamps must fall in `[0, duration_s)`. Stimulus-response analysis also needs known stimulus times and complete, nonoverlapping baseline/response windows. The upload limit is 10 MiB and 250,000 events. Pickle uploads are not accepted.

Record a citation, permission or license basis, and the source category. Uploaded provenance is an uploader assertion; schema validation cannot authenticate a biological recording. Original CSV bytes and their hash are retained for evidence export.

For a FinalSpark offline export, choose **FinalSpark recording import**. The uploader also accepts `Time,channel` CSVs with ISO-8601 timestamps when you supply an explicit timezone-aware recording start, for example `2026-01-01T00:00:00Z`. The adapter converts absolute times to recording-relative seconds; it does not open a provider network session.

## Published BrainDance analysis

The included neutral run-summary CSV was extracted from the hash-pinned [Zenodo v2 artifact](https://zenodo.org/records/17684862) under **CC BY 4.0**, with attribution and transformation details. It contains **426 runs across 16 organoid IDs and 38 experiments**. The publisher's landing page describes 432 cycles and 19 organoids; the app discloses that discrepancy and uses the file's computed counts.

This is secondary analysis of processed run summaries. It does not reproduce raw electrophysiology preprocessing or the full paper. The published `top_decile` metric is displayed in **source reward units**, because the documentation's time interpretation differs from the source code's accumulated step rewards. Repeated runs are aggregated within organoid and condition before paired comparisons.

See [BrainDance methods and provenance](docs/BRAINDANCE.md) for source hashes, the extraction procedure, and limitations. The large original pickle is not bundled and is never executed by the application.

## Verify and test

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_evidence.py /path/to/pyrexia-evidence.zip
```

With the app running and Chromium installed, `.venv/bin/python scripts/browser_smoke.py` exercises the guided workflow, published BrainDance analysis, evidence download, independent verification, and mobile layout. Set `CHROMIUM_PATH` if the executable is elsewhere. See [validation results](docs/VALIDATION.md) for the delivered revision.

The verifier checks manifest coverage and hashes, requires the bundled analysis source to match the trusted checkout, and recomputes the complete saved result. It never executes code from an archive. A successful hash check establishes integrity relative to the manifest, not identity, acquisition authenticity, biological learning, or scientific validity.

## Runtime storage and scope

`PYREXIA_DATA_DIR` defaults to `./data`. SQLite stores recordings and run history there; runtime data is excluded from version control. History survives an ordinary restart on the same filesystem. Replit deployment filesystems may be replaced during redeploys: arrange supported persistent storage and backups before relying on retained uploads. This is a single-user demo, not a multi-tenant research repository, clinical system, or laboratory controller.

The API is suitable for later Relevance AI workflow orchestration. Relevance AI, Google Drive, email, calendar, HubSpot, and provider accounts are not automatically connected by importing the code. Existing ChatGPT connections do not transfer to the app.

## Documentation

- [Academic demo walkthrough](docs/DEMO_GUIDE.md)
- [Scope, acceptance checks, and remaining work](docs/SCOPE_AND_ACCEPTANCE.md)
- [Provider access and orchestration contracts](docs/INTEGRATIONS.md)
- [Paste-ready Replit build prompt](docs/REPLIT_PROMPT.md)

No open-source license has been selected for Pyrexia application code. Third-party packages and the attributed BrainDance dataset retain their own licenses.

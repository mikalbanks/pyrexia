# Paste this into Replit Agent

Build and finish the **Pyrexia Lab MVP** from the source project I have imported into this Replit workspace. This must be a working application I can demonstrate to Georgia Tech or Emory researchers, with reproducible computations and a clear account of what is connected. Those institutions are prospective reviewers; do not imply endorsement or partnership.

If the workspace is empty, first import https://github.com/mikalbanks/pyrexia or use the Pyrexia source ZIP I supplied. Do not invent a successful import or silently start an unrelated scaffold. Inspect the actual files before editing. Preserve and improve the working implementation.

## Product and implementation

Pyrexia is the software environment for **describe an experiment → select a supported source → run → analyze → reproduce → share** across compatible biological-computing workflows. Deliver all four connected modules: **Connect, Studio, Intelligence, and Evidence**.

The starter uses Python 3.12, FastAPI, SQLite, Plotly served locally, and a responsive HTML/CSS/JavaScript workstation. Use its single-process architecture and provider interfaces. `.replit` runs `bash scripts/start.sh` on port 3000. Earlier planning mentioned Streamlit; this implementation uses FastAPI so the same scientific backend can serve the dashboard and future agent workflows. Keep the scientific calculations in reviewed Python code.

Read `README.md`, `docs/SCOPE_AND_ACCEPTANCE.md`, `docs/INTEGRATIONS.md`, `docs/BRAINDANCE.md`, `docs/DEMO_GUIDE.md`, and the existing tests before making changes. Fix demonstrated defects and complete the acceptance checks below. Do not replace working analysis with canned charts or prewritten success messages.

## Required working workflows

1. **Connect and provenance.** Generate seeded Pyrexia synthetic recordings; import authorized UTF-8 spike CSVs; capture the official Cortical Labs SDK simulator when installed; and exercise the FinalSpark offline normalization adapter with explicit fixtures. Every dataset, result, chart, and exported package must carry the real source mode. A generated fixture must never be presented as vendor data, a published recording, or a live connection.
2. **Studio.** Configure and save platform-independent experiment specifications. Support stimulus-response and signal-stability recipes, explicit recording duration/channel count, stimulus times where required, bin/window parameters, research notes, and persistent run history. The objective helper must be clearly labeled as rules-based unless an actual optional model integration is implemented and tested.
3. **Intelligence.** Show interactive spike rasters, firing rates, channel activity, descriptive metrics, methods, and limitations. Compare saved runs and flag incompatible recipes, settings, or data sources. Matching settings do not prove equivalence between biological preparations.
4. **Published BrainDance analysis.** Use the bundled neutral CSV and source provenance, not synthetic substitute results. Analyze the actual processed run summaries, group repeated runs within organoid and condition, show condition comparisons and the paired sample count, and preserve the source reward units. The pinned file contains 426 runs, 16 organoid IDs, and 38 experiments; disclose that its counts differ from the landing page's 432 cycles/19 organoids. This is secondary analysis, not full-paper reproduction or proof of learning. Verify the CSV hash before analysis.
5. **Evidence.** Export complete normalized inputs, original imported CSV bytes when applicable, dataset/source metadata, experiment parameters, results, analysis source, versions, and a SHA-256 manifest. Download a real ZIP and independently recompute it with `scripts/verify_evidence.py`. Tampering must fail verification. Do not execute archive code. Explain that integrity checks do not authenticate recordings or scientific claims.
6. **Demonstration quality.** Keep the responsive research workstation clear on desktop and mobile. Ensure real loading, error, empty, and success states, keyboard-accessible controls, readable chart units, working navigation, and an academic demo guide. All visible buttons must perform their stated operation.

## Provider boundaries

- Use Python **3.12**, the compatible target for the documented SDK versions.
- The optional Cortical package is `cl-sdk==1.0.0`. It has a **CC BY-NC 4.0** license: preserve attribution and the research/demo limitation. Do not represent it as commercially cleared. The app must confirm simulator mode before `cl.open()` and must not call live laboratory controls. The official default simulator generates non-learning data; it does not prove biological adaptation.
- FinalSpark live access requires provider authorization, connectivity, and validated SDK configuration. The delivered offline adapter normalizes documented `Time`/`channel` exports using an explicit timezone-aware recording start. Its generated test fixture validates parsing only. Do not fabricate credentials, a public API endpoint, a successful SDK session, or a live result. Show access requirements and honest failures. The public viewer can be linked separately.
- Keep live CL1 control, live FinalSpark experiments, closed-loop biological training, and native hardware acquisition clearly pending until authorized access and operator validation exist. Do not bypass access barriers.
- The BrainDance processed data and Cortical simulator are different workflows. Do not force trial-performance summaries into spike-event analysis recipes.

## Future orchestration and broader scope

Keep the existing documented REST API suitable for future Relevance AI research, reproduction, evidence, development, and scientific-review agents. Workflow agents may submit reviewed analysis jobs and retrieve results; Python performs the calculations. Record integration contracts and readiness truthfully.

Google Drive evidence archiving, Relevance AI, email, calendar, HubSpot, and provider-account authorization are separate integrations. Connections available in another chat do not automatically exist here. Do not claim they are connected, send outreach, create CRM entries, or configure external automations merely because this prompt mentions them. List each missing connection and its exact next step.

The longer-term roadmap includes programmable experiments, broader benchmarks, conventional-compute baselines, and whole-system energy measurements. No measured biological computing advantage, energy savings, learning result, clinical value, customer traction, financing, or institutional relationship can be claimed from this MVP. Preserve these directions in the roadmap without inventing results. Earlier company-planning archives and financial models are separate artifacts, not assumed to be present in this checkout.

## Run and validate

Install the project using the existing Python environment and lock dependency versions as appropriate. Start with base dependencies; install the optional Cortical research extra when the environment supports it and test a real short SDK acquisition. Keep the base synthetic/import/analysis/evidence workflow operational if that extra is unavailable. Do not automatically purchase plans, enable paid services, or require a model key for the core demo.

Run the complete test suite and report exact results. Use browser tests against the actual app to verify:

- Guided synthetic demo through analysis and evidence download.
- A second run and an actual comparison.
- Valid CSV import, rejected malformed/out-of-range data, and explicit source metadata.
- Cortical SDK acquisition when installed, with simulation provenance and an honest unavailable state otherwise.
- FinalSpark fixture normalization with explicit fixture labels.
- Published BrainDance analysis with source hash, actual counts, paired grouping, correct units, and limitations.
- Evidence ZIP verification and failure after a payload is modified.
- History persistence after restarting on the same filesystem.
- Desktop and narrow mobile layouts, keyboard navigation, and no console/network errors.

For a hosted demo, require a `PYREXIA_DEMO_PASSWORD` secret of at least 12 characters and username `pyrexia`; never put the value in source or logs. Confirm that reverse-proxy origin handling and the browser preview work in Replit. Document whether the chosen deployment has persistent storage. Do not assume SQLite files survive redeployment or represent this demo as a multi-user production service.

## Required final deliverables

Return a runnable preview URL, the source changes or Git commit, exact passing/failing test output, a downloaded synthetic evidence ZIP with successful independent verification output, a published BrainDance result/export, and a concise list of remaining access-dependent work. Include the five-minute demonstration sequence and commands to reproduce the run from a fresh workspace.

State precisely whether a Replit deployment was created or only a development preview is running. If the environment cannot run a dependency or a provider needs access, complete all independent workflows and report the specific blocker. The acceptance target is a functional, inspectable MVP, not a landing page, a simulated integration status, or a promise to build later.

# MVP scope and acceptance

Pyrexia Lab v0.5 is a demonstrable research software workstation. The minimum useful loop is **configure a source → execute a real calculation → inspect provenance and methods → export → independently recompute**.

## Scope traceability

| Earlier objective | Delivery or present boundary | Acceptance evidence |
| --- | --- | --- |
| Connect, Studio, Intelligence, Evidence | Four working dashboard modules backed by Python services | Browser walkthrough and API responses |
| One-click experiments / Pyrexia Gym | Seeded synthetic recording plus a configured analysis | Guided demo yields actual events, metrics, plots, and saved run |
| Neural recording upload | Normalized CSV with explicit observation metadata and provenance | Valid import succeeds; invalid channels, timestamps, schema, and size are rejected |
| Stimulus response and signal stability | Deterministic descriptive analyses | Hand-calculated test cases, silent channels, partial bins, invalid/overlapping windows |
| Official Cortical Labs integration | Optional bounded acquisition through the actual SDK simulator | SDK subprocess output, recorded version/seed, simulator guard tests |
| FinalSpark integration | Documented offline export normalization and generated fixture tests | UTC-aware normalization tests and truthful readiness state; live SDK session remains pending |
| BrainDance analysis | Actual published processed run-summary CSV and organoid-level descriptive comparison | Source/normalized hashes, actual file counts, grouping tests, limitation disclosure |
| Platform-independent experiment format | Recording metadata, saved analysis parameters, and evidence engine/schema versions | Exported `dataset.json`, `experiment.json`, and `environment.json` |
| Analysis comparisons | Side-by-side saved runs with compatibility warnings | Actual comparison output and incompatible-settings test |
| Scientific evidence vault | Inputs, parameters, source, results, versions, hash manifest | Downloadable ZIP and independent recomputation; tampering fails |
| Describe an experiment | Transparent keyword-based recipe suggestion | Rules-based label and inspectable plan; no LLM or scientific-review claim |
| Share and preserve results | Downloadable evidence packages and source project | Files can be reviewed independently; automatic Drive publication is not implemented |
| AI workforce | REST API and documented orchestration boundary | Scientific compute stays in Python; actual Relevance AI account connection remains pending |
| Energy / conventional-compute benchmarks | Roadmap with measurement requirements | No synthetic energy numbers or biological advantage claims |
| Research collaboration / company planning | Academic demonstration guide and scoped evaluation questions | No invented partners, customers, funding, endorsements, or revenue results |

## Acceptance checks

1. A fresh Python 3.12 checkout starts using documented commands and `.replit` without a paid API key.
2. The guided demo creates a real synthetic event dataset and computes stimulus-response metrics. The data, run, and evidence retain synthetic provenance.
3. Signal-stability analysis includes all declared channels and normalizes partial bins by their actual observation time.
4. A CSV upload requires explicit duration/channel count and rights confirmation. The normalized input and original uploaded bytes are preserved with separate hashes.
5. Stimulus-response windows must fit inside the observation interval and must not overlap. Invalid configuration returns a readable error.
6. The optional Cortical integration executes `cl-sdk==1.0.0`, records the version and simulation configuration, and refuses hardware mode before opening a source. Missing dependency is reported accurately.
7. FinalSpark offline normalization handles documented `Time`/`channel` records with an explicit timezone-aware recording start. Fixture provenance cannot be mistaken for a vendor recording.
8. BrainDance analysis verifies the neutral CSV hash, reports the file's computed counts, aggregates repeated runs within organoid/condition, and uses source reward units. It exposes the limitations and landing-page discrepancy.
9. Two saved runs can be compared. Different recipes, analysis settings, recording durations, channel counts, stimulus schedules, or source modes produce compatibility reasons.
10. A downloaded evidence ZIP verifies independently using trusted code. Changed inputs, results, code, omitted manifest entries, extra files, unsafe paths, or inconsistent metadata fail.
11. Run history remains after restarting with the same `PYREXIA_DATA_DIR`. Runtime recordings and secrets are excluded from Git.
12. The actual UI works on desktop and a narrow viewport, with readable forms, keyboard-accessible navigation, useful error states, and no failed application assets.
13. A detected Replit deployment without a sufficiently long demo password refuses to serve the workspace. Authentication and same-origin writes work through the intended preview/deployment route.

Use the repository test suite and real browser checks. Test totals belong in the validation report for the exact tested revision; this document does not hard-code a passing count.

## Access-dependent next work

| Work | What is needed before calling it complete |
| --- | --- |
| Replit preview or deployment | Import this source into Replit and execute the documented acceptance checks there |
| Live Cortical CL1 | Authorized device/cloud access, applicable license, deployment architecture, operator validation, and actual integration tests |
| FinalSpark read-only SDK session | Provider-approved access, lab connectivity, SDK installation/configuration, recorded-query validation, and authorized sample data |
| Laboratory-changing operations | Separate reviewed scope and operator validation; no such endpoint exists in this MVP |
| Full BrainDance paper reproduction | Raw/preprocessed source definitions, paper methods, exact analysis code/version, and independent scientific review |
| Google Drive archive | Dedicated account authorization, agreed destination/access, and an upload integration |
| Relevance AI workforce | Project connection, tool permissions, configured API access, and end-to-end workflow tests |
| Email/calendar/CRM | Separate connected accounts and explicit workflows; no outreach is sent by the app |
| Multi-user hosted research product | User identities, access isolation, durable database/object storage, backups, retention controls, and deployment validation |
| Compute/energy advantage | Equivalent task and quality criteria, measured whole-system energy including life support/supporting compute, uncertainty, controls, and independent replication |

## Prior artifacts

Earlier chats referenced BrainDance prototype ZIPs, a startup source-of-truth folder, a YC draft, and a financial workbook. Their original files were not available in this checkout. This MVP recovers the product requirements and documents their connection to the current implementation; it does not pretend those old files were imported or that their original test reports validate this revision.

Company pricing, financing, patentability, and customer-demand statements remain hypotheses or separate business work. They are not acceptance criteria for the research application and are not represented as demonstrated outcomes.

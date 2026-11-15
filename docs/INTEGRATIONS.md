# Provider and workflow integrations

Pyrexia owns its normalized recording format, experiment specifications, calculations, and evidence pipeline. Provider adapters translate supported inputs into that format. A matching schema does not establish equivalent hardware capabilities or biology.

## Current capabilities

| Source | Implemented | Access and limitations |
| --- | --- | --- |
| Pyrexia synthetic engine | Seeded, independently authored Poisson spike generator | No external service; response rates are programmed inputs |
| Cortical Labs SDK | Actual short simulator acquisition in an isolated subprocess | Optional `cl-sdk==1.0.0`; simulator-only guard; CC BY-NC 4.0 |
| Cortical Labs CL1 live | Readiness information only | Requires authorized device/cloud access; no live-control endpoint |
| FinalSpark offline export | Normalization of documented `Time`/`channel` rows | Explicit timezone-aware start, duration, channel count, and provenance; fixture generated locally |
| FinalSpark live NeuroPlatform | Readiness information and official links | No authorized SDK network session implemented; provider access and connectivity required |
| BrainDance recordings | Normalized spike CSV import | User supplies authorized data, citation, permission, duration, and channel count |
| Published BrainDance summaries | Bundled neutral run-summary CSV with pinned source provenance | Separate trial-performance analysis; not raw neural recording analysis or full-paper reproduction |

## Cortical Labs

Official resources: [SDK documentation](https://docs.corticallabs.com/), [source](https://github.com/Cortical-Labs/cl-sdk), and [license](https://github.com/Cortical-Labs/cl-sdk/blob/main/LICENSE).

The optional extra installs `cl-sdk==1.0.0`. Python 3.12 satisfies the documented SDK requirement and the FinalSpark v2 Python compatibility range. The worker clears inherited SDK configuration, disables dotenv loading, bounds acquisition and process lifetime, verifies `cl.is_simulator() is True`, and records configuration and SDK version with each dataset.

The simulator supports compatibility development. Its default generated control data does not learn or respond to stimulation. Never relabel it as live tissue or use it to claim a learned task. The package's CC BY-NC 4.0 license must be considered before commercial use; the base application does not require this dependency.

## FinalSpark

Official resources: [v2 SDK documentation](https://finalspark-np.github.io/np-docs/np_core/doc_v2.html), [NeuroPlatform and access requests](https://finalspark.com/neuroplatform/), [public viewer](https://finalspark.com/live/), and [LiveMEA utility source](https://github.com/FinalSpark-np/LiveMEA).

`FinalSparkReadOnlyAdapter.normalize(...)` accepts documented export rows with `Time` and `channel`, an explicit timezone-aware recording start, duration, and channel count. It converts times to relative seconds and rejects ambiguous numeric epochs, naive timestamps, or out-of-range rows. The included fixture exercises this adapter with generated data.

The documented `neuroplatformv2` SDK and a public README do not grant a laboratory session. Live use needs approved access, lab network connectivity, installation/configuration supplied by the provider, and validated read-only queries. A future adapter should retrieve a bounded historical recording, preserve the original query and provenance, and feed the same normalized analysis interface. It must report permission/network failures and never silently substitute synthetic results.

The public LiveMEA viewer is an external observation route. Its service was unavailable during the initial source check; this MVP does not claim a verified live feed. Do not invent a sample rate or treat a public viewer as authorized laboratory control.

## Scientific workflow API

The FastAPI schema at `/api/docs` describes the current interface. A workflow agent can use this sequence after its own project connection and app access are configured:

1. Read `/api/state` and inspect provider/source readiness.
2. Create a supported synthetic dataset or import an authorized CSV.
3. Submit a reviewed experiment specification to `POST /api/runs`.
4. Retrieve `GET /api/runs/{id}` and report the returned method, source, metrics, and limitations.
5. Download `GET /api/runs/{id}/evidence` and request `POST /api/runs/{id}/verify`.

Example experiment body, using a real dataset ID returned by the app:

```json
{
  "name": "Recording stability check",
  "recipe": "signal_stability",
  "dataset_id": "replace-with-the-returned-dataset-id",
  "bin_s": 1.0,
  "baseline_window_s": 0.2,
  "response_window_s": 0.2,
  "notes": "Descriptive software check; review acquisition provenance separately."
}
```

The current application is a single-user research demo. Hosted instances use HTTP Basic authentication when configured, with username `pyrexia` and a server-side secret. A production agent service would need suitable service credentials, user isolation, rate limits, durable job execution, and operational monitoring before serving multiple labs.

## Relevance AI workforce

Earlier planning proposed Research, Reproduction, Evidence, Development, and Scientific Review agents. Relevance AI should orchestrate their tasks through a bounded Pyrexia API; it should not replace the numerical analysis engine or certify scientific conclusions.

| Agent | Intended responsibility | Evidence it should retain |
| --- | --- | --- |
| Research | Find relevant papers and datasets | Source URLs, citations, retrieval dates, permission/license facts |
| Reproduction | Submit a reviewed supported analysis | Dataset ID/hash, exact specification, run ID, returned status |
| Evidence | Collect and verify exports | Export identifier, verifier output, source mode, integrity limitations |
| Development | Track implementation work | Concrete issues, commits, test output, and access blockers |
| Scientific Review | Flag unsupported claims and method gaps | Specific result/method references and unresolved questions |

No Relevance AI project is configured by this repository. ChatGPT/GitHub connections do not transfer automatically. Connect the intended Relevance AI project, assign only the required tools, configure access to the running Pyrexia instance, and test one synthetic workflow before expanding permissions. Do not embed service credentials in this repository or evidence ZIPs.

## Business and archive services

Google Drive evidence storage, email, calendar, HubSpot, and GitHub development workflows are separate integrations. The current application exports files suitable for an agreed archive, but it does not upload to Drive, send outreach, schedule meetings, or change CRM records. Each workflow needs its own account authorization, destination/scope, and end-to-end test.

Keeping these connection states accurate is part of the MVP: a configured account, a provider with documentation, a passing parser fixture, and a verified live session are different milestones.

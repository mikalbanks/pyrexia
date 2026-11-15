# Internal implementation contract

Python 3.12, FastAPI, sqlite3, NumPy, Plotly served locally. Single process serves API and static HTML/JS/CSS. No paid service required. Modules: Connect, Studio, Intelligence, Evidence. Runtime working data at PYREXIA_DATA_DIR (default ./data), never committed.

## Dataset
`{id,name,source_kind,duration_s,n_channels,event_count,created_at,sha256,provenance,stimuli_s}`. Raw normalized events are `[{timestamp_s:float,channel:int}]`. Channel ids 0..n_channels-1; timestamps 0<=t<duration_s. Dataset duration is explicit (never inferred from last spike). `provenance` must distinguish user assertions and verified facts. Synthetic / SDK simulator / test fixture are never biological evidence.

## Experiment spec
`{name,recipe,dataset_id,bin_s:1.0,baseline_window_s:0.2,response_window_s:0.2,notes:""}`. Recipes `stimulus_response` and `signal_stability`. Dataset has `stimuli_s` for response; imported stimuli can be supplied as JSON array in upload metadata. Validation errors return HTTP422 with readable detail. Response windows cannot overlap each other or baseline windows; reject invalid windows, do not silently double count.

## API for frontend
- GET /api/state -> `{version,datasets,runs,providers,templates}`
- POST /api/datasets/synthetic JSON `{name,seed,duration_s,n_channels,baseline_hz,response_hz}` -> Dataset. Defaults name='Synthetic response demo', seed=42,duration_s=30,n_channels=8,baseline_hz=3,response_hz=12. Stimuli generated at known intervals.
- POST /api/datasets/upload multipart `file`, `name`, `duration_s`, `n_channels`, `stimuli_s` (JSON string), `citation`, `license`, `source_kind` (uploaded or braindance_upload or finalspark_upload), `confirmed_rights` (true required) -> Dataset. CSV timestamp_s,channel required. 10 MiB limit.
- POST /api/datasets/cortical JSON `{duration_s:2,seed:42}` -> Dataset from official cl-sdk simulator. Must never use live hardware. Show missing dependency/error honestly.
- POST /api/datasets/fixture JSON `{kind:'finalspark'|'braindance'}` -> Dataset; generated representative test fixture always labeled test data.
- GET /api/datasets/{id} -> Dataset plus `events` (max10000 for display, `display_truncated`), no data mutation.
- POST /api/runs JSON experiment spec -> Run.
- GET /api/runs/{id} -> Run plus `dataset` metadata and plot data in result.
- GET /api/runs/{id}/evidence -> ZIP download.
- POST /api/runs/{id}/verify -> `{verified,checks,details}` recompute evidence.
- POST /api/compare JSON `{run_ids:[id,id]}` -> `{runs,comparable,reasons}` (metric table; no cross-platform biological equivalence claim).
- POST /api/plans JSON `{objective}` -> structured suggested recipe + explanation; rules-based assistant clearly labeled; no LLM key needed.
- GET /api/health -> readiness.

## Analysis module interface
`analyze(events: list[dict], metadata: dict, spec: dict) -> dict` pure JSON return. Top-level `{recipe,metrics:dict,warnings:list[str],plots:{raster:{x:[],y:[]},firing_rate:{x:[],y:[]},channels:{x:[],y:[]}},method:dict}`. Include measured units in metric names. All floats finite or null; sort normalized events; deterministic.

## Provider module interface
`provider_status() -> list[dict]` each `{id,name,status,label,description,kind,documentation_url}`.
`synthetic_dataset(config:dict) -> (events:list[dict],metadata:dict)` metadata duration_s,n_channels,stimuli_s,source_kind,provenance,name.
`fixture_dataset(kind:str) -> (events,metadata)` distinct honest fixture labeling.
`cortical_dataset(config:dict) -> (events,metadata)` actual optional cl-sdk acquisition, read-only simulator only. Missing SDK raises ValueError; metadata includes SDK version and generation parameters. `FinalSparkReadOnlyAdapter` normalizes documented offline spike export fixture and exposes explicit no-credentials readiness; no network hardware calls.

## Evidence
ZIP normalized input CSV, dataset.json, experiment.json, result.json, analysis.py and needed standalone dependencies/source, README, requirements/version metadata, manifest SHA256s. Independent command scripts/verify_evidence.py ZIP validates hashes, rejects extras/path traversal, recomputes result. No secrets. Content hash validates integrity, not authenticity of a recording. Include analysis runtime/engine version, seed, timestamps, provider mode.

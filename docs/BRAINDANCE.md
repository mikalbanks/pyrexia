# Published BrainDance secondary analysis

Pyrexia includes neutral run summaries derived from Robbins, A., et al. (2025), *Goal-Directed Learning in Cortical Organoids - Experimental Data and Code*, Zenodo v2, [DOI 10.5281/zenodo.17684862](https://doi.org/10.5281/zenodo.17684862), licensed CC-BY-4.0. The data was collected by the source researchers, not by Pyrexia. This demonstration implies no affiliation or endorsement.

The source is a published processed recording archive. Pyrexia retains experiment metadata and each CartPole run's published `top_decile`, counts reward-log episodes, and computes the mean episode reward. It omits raw game trajectories, baseline arrays, and causal connectivity arrays. It does not recreate the source paper's entire analysis or raw electrophysiology preprocessing.

The source [schema documentation](https://zenodo.org/records/17684862/files/README_data_structure.md?download=1) identifies `metadata.organoid` as the deduplicated grouping identifier; raw chip IDs can be reused. Conditions are `rl` (adaptive), `random`, and `none`. The default comparison includes only `cycled` experiments, where conditions alternate; continuous adaptive-only experiments can be inspected separately. First average run-level top-decile rewards within each organoid and condition. Then calculate paired adaptive-minus-control differences for organoids having both conditions. Each organoid has equal weight. No p-value or causal-learning conclusion is reported. Run order, carryover, culture batch, and unequal observations can affect the comparison.

Two source discrepancies remain visible in the application and evidence export:

- The Zenodo landing-page description says 19 organoids and 432 training cycles. The exact v2 file contains 16 deduplicated organoid IDs, 38 experiments, and 426 CartPole runs. Pyrexia reports counts computed from the file.
- The README describes rewards as time balanced, while the provided `phases.py` accumulates environment-step rewards. Pyrexia preserves source reward units and does not convert them into wall-clock seconds.

`pyrexia/resources/braindance_source.json` records citation, license, original hashes, transformations, and limitations. `braindance_runs.csv` contains one row per source run, not one row per biological replicate. The CSV SHA256 is checked before analysis. This verifies integrity against the accompanying provenance; it does not authenticate the underlying recording.

Rebuild the shipped summaries from the exact public source using Python 3.12 and the standard library:

```sh
python scripts/prepare_braindance.py --download
```

Or pass a previously downloaded source file:

```sh
python scripts/prepare_braindance.py /path/to/aggregated_experiment_data.pkl
```

The original source is approximately 83.2 MB and is not committed. The converter requires SHA256 `e84484e116187448dbba1c6860c5970b6ae2bc7a58f20b3a1525d0b5dedb0fd5` and its MD5 matches the publisher's listed `af99f1f859136ca4a6dad47a1aa7c86d`. It scans pickle opcodes and uses a restricted decoder mapping only three reviewed NumPy names to local inert types/functions. Baseline arrays are discarded without reconstructing NumPy objects. No publisher code, NumPy constructors, arbitrary pickle globals, or persistent IDs run. This tool supports one reviewed artifact; it is not a general pickle importer. Runtime web uploads never accept pickle files.

The application can export a ZIP containing normalized CSV, source provenance, summary JSON, a standalone stdlib analysis module, and a SHA256 manifest. Verify it with a trusted copy of the installed module:

```sh
python -m pyrexia.braindance --verify /path/to/braindance-evidence.zip
```

After extracting the archive, independently recompute using its analysis module:

```sh
python braindance.py --csv runs.csv --paradigm cycled --output recomputed.json
```

Compare `recomputed.json` with `summary.json`. Review code before executing it from an untrusted archive. Verification validates archive structure, file hashes, normalized source hash, and numerical recomputation using the verifier's own analysis implementation.

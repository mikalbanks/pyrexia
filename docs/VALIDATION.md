# Validation of the delivered MVP

Validated on Python 3.12.14 with Chromium, using the code and pinned direct dependencies in this repository.

- `python -m pytest -q`: **97 passed**, plus 24 unittest subtests. This includes an actual optional Cortical SDK subprocess acquisition and reproducibility check. A base-only installation skips that SDK acquisition test when `cl-sdk` is absent.
- `python scripts/browser_smoke.py`: passed guided synthetic generation, analysis, charts, published BrainDance analysis, downloaded evidence, independent CLI recomputation, and a 390-pixel mobile layout. No JavaScript page errors or failed HTTP responses occurred.
- Additional browser checks passed normalized CSV import, FinalSpark `Time,channel` offline import with an explicit UTC recording start, rules-based planning, comparisons, fixture labels, and all five navigation views at mobile width.
- `uv build --wheel`: succeeded with frontend assets and the attributed BrainDance CSV/JSON resources included.
- `node --check pyrexia/web/app.js` and `git diff --check`: passed.
- Full HTTP workflow with the installed official Cortical SDK: acquired 152 simulated spikes over two simulated seconds across 64 channels (seed 42), ran signal-stability analysis, downloaded the ZIP, and independently verified it. The published BrainDance HTTP analysis/export also verified independently.

Analysis tests cover known-count calculations, silent channels, partial bins, decimal bin/window boundaries, overlap rejection, and empty recordings. Evidence tests cover full manifest coverage, altered inputs/results/source, original uploaded bytes, bounded parsing, and independent recomputation. API tests cover persistence, input validation, provenance, authentication, and deployment refusal without a configured demo password.

BrainDance checks verify the packaged source hash and report 426 total runs across 16 organoid IDs and 38 experiments. The default cycled analysis selects 288 runs across 12 organoids, with paired sample sizes reported per control. This is a descriptive secondary analysis in source reward units.

These checks establish local software behavior. Replit preview/deployment and its persistent storage must still be validated in that environment. Live provider hardware access and complete scientific reproduction are separate milestones; see [scope and acceptance](SCOPE_AND_ACCEPTANCE.md).

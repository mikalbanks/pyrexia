# Academic demonstration guide

The purpose of a Georgia Tech or Emory meeting is to show a working software pipeline and identify a scientific validation project. Neither institution is represented as a partner or endorser.

## Before the meeting

1. Start the app with Python 3.12 and verify `/api/health` returns `status: ok`.
2. Run the test suite. If showing the Cortical integration, install the optional research extra and complete one actual simulator capture in the same environment.
3. Open the app on the presentation device and download a fresh evidence ZIP. Verify it from a terminal using trusted project code.
4. Check the BrainDance analysis and its source hash. Keep the published dataset attribution and limitations available.
5. If sharing a hosted preview, configure the demo password, confirm the intended audience, and test the link from a second browser. Preserve local copies of demonstration exports.

## Five-minute core walkthrough

| Time | Action | What it demonstrates |
| --- | --- | --- |
| 0:00–0:40 | Open **Studio** and choose **Run guided demo** | A question can lead to a configured, computed experiment without a hardware account |
| 0:40–1:30 | Inspect the raster, rate, channel plots, and source badge | Data, observation duration, units, and synthetic provenance stay visible |
| 1:30–2:15 | Run signal stability on the same recording; open **Intelligence** | One source can support a second real analysis; experiment settings and methods are saved |
| 2:15–3:00 | Open published **BrainDance** analysis and inspect organoid-level comparisons | The pipeline can analyze real published processed summaries with traceable provenance and explicit limitations |
| 3:00–4:10 | Open **Evidence**, download a ZIP, and verify it independently | Saved inputs, parameters, source, and results can reproduce the complete computed result |
| 4:10–5:00 | Open **Connect** and explain provider readiness | Official SDK simulation works where installed; laboratory access and biological validation remain concrete next steps |

If the SDK is installed, add a short Cortical simulator capture and run **signal stability** on its output. Do not invent stimulus times for the SDK's random source. Compare the source badges and recorded SDK version with those of Pyrexia's own synthetic generator.

## Language to use

> Pyrexia is a working software layer for configuring, analyzing, and reproducing supported biocomputing workflows. Today we can demonstrate deterministic synthetic experiments, an official Cortical SDK simulator integration, imported recordings, published BrainDance summary analysis, and evidence exports that recompute independently. We are seeking researchers to help validate the workflow on authorized recordings and define the next experiment.

Keep the claims tied to the source:

- **Synthetic:** programmed activity tests the software. An apparent response was an input to the generator.
- **Cortical SDK simulation:** real SDK execution and software interoperability; default simulated activity does not establish learning.
- **FinalSpark fixture:** locally generated examples test the offline normalizer. They are not FinalSpark recordings or a live session.
- **Uploaded recording:** the uploader declares origin and permission. Pyrexia validates structure and records that assertion.
- **BrainDance published summaries:** a descriptive secondary analysis of processed published runs. This does not reproduce the full study or establish causal learning.

The pinned BrainDance file contains 426 runs, 16 organoid IDs, and 38 experiments. Explain the discrepancy with the landing page's 432 cycles/19 organoids. Use **source reward units**, not seconds; documentation and code differ on that interpretation.

## Evidence demonstration

After downloading a package:

```bash
.venv/bin/python scripts/verify_evidence.py /path/to/pyrexia-evidence.zip
```

Show `verified: true`, the payload hashes, source-match check, and recomputed result. Explain that the verifier uses trusted checkout code and never runs code from the archive. Hashes protect integrity relative to the manifest; an unsigned manifest cannot authenticate who acquired a recording.

## Suggested research discussion

- Which current workflow loses the most time: normalization, experiment setup, repeated analysis, cross-session comparison, or preparing reproducibility artifacts?
- Can a lab supply an authorized recording, its observation metadata, stimulus schedule, and an expected result for a blinded software check?
- What constitutes successful reproduction for one narrowly defined analysis?
- Which biological preparation, controls, and independent replicates would be required before making a learning claim?
- Does the lab need a read-only import tool, an adapter running inside its network, or a hosted interface?

Propose one bounded evaluation with a named dataset, method, expected output, and reviewer. Record limitations and follow-up questions. This guide does not authorize sending outreach or configuring laboratory equipment.

## Demonstration limits

There is no live CL1 or FinalSpark laboratory session, validated clinical use, measured energy advantage, production multi-user isolation, or full-paper reproduction. Google Drive, Relevance AI, email, calendar, CRM, and provider-account connections remain separate authorization work. The app's history persists on its current filesystem; hosting redeploys need persistent storage and backups.

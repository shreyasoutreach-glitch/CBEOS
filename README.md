# CBEOS — CBAM Evidence Control Tower

> **Publication status: PARTIAL SOURCE SNAPSHOT. Do not deploy this branch.**

CBEOS is intended to provide traceable CBAM evidence intake, reconciliation exceptions, supplier evidence workflows, controlled calculations, and review-ready records. This GitHub repository does **not yet contain the complete local application source tree**; key runtime modules, tests and tools are absent. Local test results must not be interpreted as remote verification for this repository snapshot.

## What has actually been verified

- Local working tree: 9 regression suites passed and Python compilation passed on 9 October 2026.
- GitHub Actions: workflow ran. Dependency audit passed with **“No known vulnerabilities found”** for the currently published dependency set. Compilation passed but warned that `tools` and `tests` were missing. The regression step failed because `tests/run_all.py` is not yet in the GitHub tree.
- Legal source gate: **blocked**. 7 curated canonical-source spot checks only; 14,620 of 14,627 staged rows remain pending reconciliation. Pending means not reconciled, not necessarily incorrect.
- Deployment and Antigravity independent verification: not performed.

See [PUBLICATION_STATUS.md](PUBLICATION_STATUS.md), [RELEASE_STATUS.json](RELEASE_STATUS.json), [SPRINT_MASTER_PLAN.md](SPRINT_MASTER_PLAN.md), and [docs/REGULATORY_SOURCE_HIERARCHY.md](docs/REGULATORY_SOURCE_HIERARCHY.md).

## Publication boundaries

- This snapshot is not runnable yet; do not deploy it.
- Do not describe CBEOS outputs as guaranteeing CBAM compliance or certification.
- Informational spreadsheets are not substitutes for legally binding EU acts.
- No regulatory data has been promoted into an approved canonical runtime dataset.
- Do not commit confidential supplier files, runtime databases, credentials, raw legal workbooks, or generated row-level reconciliation exports.

The next engineering deliverable is a complete, source-identical publication of the curated local workspace followed by a green remote regression workflow. Only then should live-host deployment and operational recovery checks begin.

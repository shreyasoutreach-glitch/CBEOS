# CBEOS — CBAM Evidence Control Tower

> Engineering preflight publication. This repository is **not production-ready** and does not constitute a legal compliance determination.

CBEOS turns supplier and trade documents into traceable CBAM evidence, reconciliation exceptions, supplier evidence workflows, and review-ready calculation records. Calculation and AI-assisted outputs are advisory until independently verified and approved by an accountable human.

## Current release gate

- Local regression suite: 9 suites, passing in the current working environment.
- Python compilation: passing locally.
- Legal-data promotion: **blocked**. Only 7 curated binding-source spot checks have been reconciled; 14,620 staged rows remain pending. Pending means not reconciled, not necessarily incorrect.
- Dependency audit: GitHub Actions configured to run `pip-audit`; remote run required to obtain an actual result.
- Deployment and live-host checks: not performed.
- Independent Antigravity review: not performed.

See [`RELEASE_STATUS.json`](RELEASE_STATUS.json), [`SPRINT_MASTER_PLAN.md`](SPRINT_MASTER_PLAN.md), [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md), and [`docs/REGULATORY_SOURCE_HIERARCHY.md`](docs/REGULATORY_SOURCE_HIERARCHY.md).

## Quickstart

```bash
python -m pip install -r requirements.txt
CBAM_ADMIN_EMAIL=you@example.com CBAM_ADMIN_PASSWORD='replace-with-a-strong-password' python server.py
```

Open `http://127.0.0.1:8000/`. Never use demo/default credentials outside a disposable local environment. The optional LLM critique integration is disabled unless explicitly configured; review provider retention, privacy, and contractual controls before enabling it.

Seed the synthetic demo data in a fresh local database with:

```bash
python -m app.demo
```

## Checks

```bash
python -m pip install -r requirements.txt pip-audit
python -m pip_audit
python -m compileall -q app tools tests
python tests/run_all.py
```

GitHub Actions runs the dependency audit, compilation check, and regression suite on pushes and pull requests.

## Important boundaries

- Source spreadsheets and indexes are supporting data, not substitutes for the legally binding EU acts.
- No regulatory dataset should be promoted until canonical-source reconciliation, discrepancy handling, source versioning, and review gates are complete.
- Never describe outputs as guaranteeing CBAM compliance or certification.
- Do not use live supplier/client confidential data without approving access, privacy, and provider controls.
- SQLite recovery tooling is local-only until off-host backups, retention, encryption, alerting and a live recovery drill are configured.

## Project status

This first GitHub publication captures the tested engineering preflight and its open gates. Sprints may have implemented baselines, but the release remains **NOT_PRODUCTION_READY** until blocked legal, external security, deployment, operational recovery and independent-review checks are closed.

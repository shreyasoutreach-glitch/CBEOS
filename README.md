# CBEOS | CBAM Evidence Control Tower

> **Status: engineering candidate. Not production-ready. Do not use for live CBAM filing or liability decisions.**

CBEOS is a control-tower prototype for CBAM evidence intake, traceable import-line records, supplier evidence operations, exception queues, source-aware calculation controls, verifier-readiness checks, and read-only multi-agent triage.

## Current engineering status

- Public source repository: this branch contains the runtime app modules, test suites, CI workflow, and regulatory staging/governance tools.
- CI now checks dependency vulnerabilities, Python compilation, and nine regression suites. See [GitHub Actions](https://github.com/shreyasoutreach-glitch/CBEOS/actions) for the latest authoritative result.
- Regulatory gate remains blocked: 7 curated canonical binding-source spot checks are confirmed; 14,620 of 14,627 staged records remain pending reconciliation. Pending means not reconciled, not necessarily wrong.
- No regulatory dataset has been promoted. No production deployment, off-host recovery drill, or independent Antigravity verification has been completed.
- A clean CI run is necessary but does not by itself establish regulatory correctness, security certification, or production readiness.

See [publication status](PUBLICATION_STATUS.md), [release status](RELEASE_STATUS.json), [release checklist](docs/RELEASE_CHECKLIST.md), [Antigravity verification brief](docs/ANTIGRAVITY_VERIFICATION_BRIEF.md), and [regulatory source hierarchy](docs/REGULATORY_SOURCE_HIERARCHY.md).

## Run locally

Requires Python 3.11+ and the packages in `requirements.txt`.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q app tools tests
python tests/run_all.py
python server.py
```

The demo server uses a local SQLite database. Set `CBAM_ADMIN_PASSWORD` before running and use synthetic data only. Do not expose a demo server directly to the public internet.

## Security and operating boundaries

- Tenant-scoped data access, session-bound CSRF protection, security headers, login throttling, upload checks, audit chaining, and database backup/restore tooling have regression coverage. These controls still need independent review and deployment-environment validation.
- The in-process login limiter does not share state across replicas. Upload scanning is a minimal heuristic, not a full anti-malware engine. See the code comments and release checklist.
- Optional model commentary is advisory only. Evidence verification, calculations, exception closure, approvals, and declarations remain human-controlled.
- Do not commit credentials, runtime databases, confidential supplier documents, raw legal workbooks, or generated row-level reconciliation exports.

## Regulatory source hierarchy

Binding EU legislation and applicable annexes govern legal values. Informational spreadsheets can assist discovery and reconciliation but do not override binding law. A dash, blank, parent row, or continuation row must never silently become zero or an approved default. Calculation rules fail closed for unapproved data and unresolved fallback candidates.

## Release gate

Do not deploy or use for customer work until the remote regression pipeline is green, source acquisition and full row-level legal reconciliation are complete, calculation golden cases are independently reviewed, secrets and production configuration are checked, recovery is exercised on a separate environment, and an independent reviewer signs off.

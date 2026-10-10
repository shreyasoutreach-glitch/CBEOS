# CBEOS | CBAM Evidence Control Tower

> **Status: engineering candidate. Not production-ready. Do not use for live CBAM filing or liability decisions.**

CBEOS is a control-tower prototype for CBAM evidence intake, traceable import-line records, supplier evidence operations, exception queues, source-aware calculation controls, verifier-readiness checks, and read-only multi-agent triage.

## Current engineering status

- Public source repository: this branch contains the runtime app modules, test suites, CI workflow, and regulatory staging/governance tools.
- CI checks dependency vulnerabilities, Python compilation, and the regression runner (19 suites, including operational-safety, integration-probe, recovery-workbook, and storage-adapter tests). See [GitHub Actions](https://github.com/shreyasoutreach-glitch/CBEOS/actions) for the latest authoritative result.
- Regulatory source-cell comparison is documented as complete for 14,627 staged rows (12,540 Annex I defaults, 283 Annex IV precursor defaults, and 1,804 benchmark rows) with zero machine-reported mismatches against extracted EUR-Lex table cells. This is **not** qualified legal review: completeness of annex/table extraction, effective dates, route/fallback semantics, source locators, and legal interpretation remain open; no canonical dataset has been approved or promoted. See [row-level reconciliation and golden review](docs/ROW_LEVEL_RECONCILIATION_AND_GOLDEN_REVIEW.md).
- No regulatory dataset has been promoted. No production deployment, off-host recovery drill, or independent Antigravity verification has been completed. Production mode now fails closed while the actual PostgreSQL and object-storage adapters, security/recovery approvals, and regulatory approval remain absent.
- The active candidate branch now also includes a secret-safe integration-status endpoint, provider-contract tests, an HTTP multipart-upload-to-agent-workflow regression, and Render runtime/blueprint configuration. Check [GitHub Actions](https://github.com/shreyasoutreach-glitch/CBEOS/actions) for the exact latest-head result before deploying.\n- A clean CI run is necessary but does not by itself establish regulatory correctness, security certification, or production readiness.

See [publication status](PUBLICATION_STATUS.md), [release status](RELEASE_STATUS.json), [release checklist](docs/RELEASE_CHECKLIST.md), [Antigravity verification brief](docs/ANTIGRAVITY_VERIFICATION_BRIEF.md), [regulatory source hierarchy](docs/REGULATORY_SOURCE_HIERARCHY.md), and the [iterative buyer-value audit](docs/BUYER_VALUE_AUDIT.md).

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
- The in-process login limiter does not share state across replicas. Upload scanning is a minimal heuristic, not a full anti-malware engine. An S3-compatible storage adapter is implemented, but the deployed sandbox still uses local storage; a bucket, access policy, encryption/versioning, retention and recovery must be verified before production. Sandbox uploads require an explicit synthetic-data acknowledgement, which is an accident-prevention control, not a production security boundary. See the release checklist.
- Optional model commentary is advisory only. Evidence verification, calculations, exception closure, approvals, and declarations remain human-controlled.
- Do not commit credentials, runtime databases, confidential supplier documents, raw legal workbooks, or generated row-level reconciliation exports.

## Regulatory source hierarchy

Binding EU legislation and applicable annexes govern legal values. Informational spreadsheets can assist discovery and reconciliation but do not override binding law. A dash, blank, parent row, or continuation row must never silently become zero or an approved default. Calculation rules fail closed for unapproved data and unresolved fallback candidates.

## Release gate

Do not deploy or use for customer work until the remote regression pipeline is green, source acquisition and full row-level legal reconciliation are complete, calculation golden cases are independently reviewed, secrets and production configuration are checked, recovery is exercised on a separate environment, and an independent reviewer signs off.

## Client-service scope and honest sales boundary

**What the current sandbox can demonstrate** (synthetic data only):
- Organize an importer case and import-line records.
- Record supplier, installation and evidence-request workflow states.
- Store uploaded-document metadata, content hashes and extracted candidate facts with document links, locations/excerpts and confidence where extraction supports them.
- Surface configured missing-evidence requirements and cross-document conflicts as exceptions.
- Route exception states through the application state machine and record transitions in the tenant audit chain.
- Run advisory, read-only agent triage and persist a hash-chained hand-off; show a blocked verification-readiness result and a review-package preview.
- Export a tenant-scoped, seven-sheet XLSX recovery handoff with import lines, evidence gaps, open exceptions, supplier follow-up and a document register. Suggested owner roles and next actions are recommendations for human review, not automated resolutions.
- Produce operational workflow counts for a demo. These are not proof of regulatory compliance, liability, savings or ROI.

**Not currently deliverable as a production service**:
- Authoritative CBAM liability calculations, legal interpretation, filing or compliance certification.
- A legally approved canonical regulatory dataset: machine comparison of 14,627 staged rows is documented as complete, but completeness, legal interpretation, effective dates and fallback/route semantics still require qualified review; staged data has not been approved/promoted.
- Guaranteed supplier email delivery: the supplier workflow can record request states, but do not claim an email was delivered without provider delivery evidence.
- Production-grade customer data processing, uptime/SLA, multi-replica rate limiting, full malware scanning, verified off-host disaster recovery or independent security assurance.
- Quantified customer savings, risk reduction or turnaround improvements without a measured pilot baseline and recorded outcomes.

**Sales rule:** until the exact candidate passes the seeded journey, an independent review is complete, and a sandbox deployment has been smoke-tested, sell only a discovery / workflow-mapping conversation. Do not represent CBEOS as ready to process live client documents. A later paid pilot must have a written scope, data-handling approval, synthetic/redacted test fixtures, explicit human-review responsibility, exclusions, success metrics and rollback/deletion terms.

## Engineering hand-off record (10 October 2026, IST)

Repository: [CBEOS](https://github.com/shreyasoutreach-glitch/CBEOS)  
PR: [#4, Verified candidate: client-outcomes megasprint](https://github.com/shreyasoutreach-glitch/CBEOS/pull/4)  
Branch: `meg-sprint/verified-client-outcomes-2026-10-10`  
Base: `main` at `c5f8a1d7534685db5fe8af07f86d1629681239f3`  
Current code-under-test commit: `a93c789bc7b3a57f7c49bf685ee1bbe2c11de581`  
Latest CI run for that commit: [Actions run #156](https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/38025477777). Status must be read from the live run; it was in progress when this hand-off record was authored. The last confirmed green run is #155 on commit `007bb882324dd32fdb3d77abc0b6921274d88a66`.

### Verification matrix

| Gate | Status at hand-off | Evidence / remaining work |
|---|---|---|
| Dependency audit + compile + full regression on commit `007bb882` | **PASS** | [Run #155](https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/38024911440), all steps green. |
| Dashboard and four guided HTTP destinations | **PASS on prior green head** | `tests/test_dashboard_http_journey.py`: authenticated rendering, CSP header and unauthenticated redirect checks. |
| Source provenance linkage | **TEST ADDED; exact-head CI pending** | New integration test asserts a candidate fact joins to its document, content SHA-256, filename, source excerpt and location. It does not yet prove every supported file format's extraction fidelity. |
| Exception transition and audit event | **TEST ADDED; exact-head CI pending** | New test moves a synthetic exception to `UNDER_REVIEW`, checks the audit action and deliberately tampers with a stored audit row to assert chain verification fails. |
| Agent hand-off integrity | **TEST ADDED; exact-head CI pending** | New test asserts a persisted read-only agent run completes, remains blocked when readiness is incomplete, and its message chain verifies. |
| Tenant isolation, CSRF, upload validation, backup/restore | **EXISTING REGRESSION COVERAGE** | Covered by existing suites; still needs independent security review and deployment-environment checks. |
| Full browser journey: upload through supplier, exception, verification, export and audit | **NOT YET PROVEN END-TO-END** | Existing HTTP test is primarily navigation; new provenance test seeds records at the domain/database boundary. Add multipart-upload and user-visible export/preview assertions before claiming the whole journey passes. |
| Full legal-source row reconciliation and independent arithmetic review | **BLOCKED** | No approved canonical regulatory dataset; no live liability/filing use. See [publication status](PUBLICATION_STATUS.md). |
| Antigravity independent verification | **NOT RUN** | Requires a report tied to the exact commit and artifact hashes. |
| Production or client-data deployment | **NO-GO** | No deployment, recovery drill, external review or customer-data handling gate completion is evidenced. |

### What was changed in this work session

- Added `test_seeded_case_provenance_exception_audit_and_agent_handoff` to `tests/test_integration.py`. It builds a deterministic synthetic source-document/fact relationship, checks SHA-256 and excerpt/location provenance, transitions an exception, verifies the audit chain, verifies the agent-message chain, and checks that audit tampering is detected.
- Committed as `a93c789bc7b3a57f7c49bf685ee1bbe2c11de581`.
- GitHub Actions started run #156 on that exact commit. No failure is to be marked fixed until the failing log is inspected, a code/test correction is committed, and a fresh exact-head run passes.
- No PR merge, deployment, regulatory-data promotion or client-data processing was performed.

### Next owner actions

1. Inspect run #156. If it fails, use the failing test/log to fix the root cause, commit the correction, and rerun the full pipeline.
2. Add a true HTTP multipart-upload test that verifies stored document hash, candidate-fact source location/excerpt, rejected upload rollback and no orphan file.
3. Add user-visible assertions for exception transitions, verification blockers, generated package preview/export contents, and audit view chain status.
4. Run the seeded scenario from a clean database and retain the command, exact SHA, exit code, and test artifact/log reference.
5. Ask Antigravity (or another independent reviewer) to assess the exact candidate; fix findings and rerun CI.
6. Only then perform sandbox deployment, auth/data isolation smoke tests, backup/restore and rollback verification.
7. Keep sales messaging at discovery/workflow mapping until those gates pass. A paid pilot is not cleared for live supplier documents today.

### Reproducible verification commands

```bash
python -m pip install -r requirements.txt pip-audit
python -m pip_audit
python -m compileall -q app tools tests
python tests/run_all.py
```

Record the commit SHA and exit code for every run. A green suite is evidence only for the assertions it actually executes; it is not a zero-defect or regulatory-accuracy guarantee.


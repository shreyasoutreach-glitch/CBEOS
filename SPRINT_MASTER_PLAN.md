# CBEOS Sprint Master Plan and Closeout

Updated: 10 October 2026 (IST). This is a live engineering record, not a release certificate.

## Release principle

A sprint is not “done” because code exists. Each sprint requires its deliverable, regression evidence, operational checks where applicable, and explicit blockers. The public branch is an engineering candidate. The regulatory dataset remains unapproved, and production deployment is not authorized.

## Sprint ledger

| Sprint | Workstream | Current state | Exit gate / remaining work |
|---|---|---|---|
| 1 | Legal source acquisition and reconciliation | **BLOCKED** | Acquire and hash complete binding Annex I and Annex IV sources; reconcile every staged record, classify unmatched/ambiguous/continuation rows, independently review corrected cases, then approve immutable dataset version. Seven curated spot checks are not full reconciliation. |
| 2 | Calculation rules and traceability | **Implemented baseline; review open** | Run independently reviewed golden cases against approved source rows, effective dates, reporting year, route and mark-up; preserve input snapshots; confirm every unsupported state fails closed. |
| 3 | Evidence graph and scoped requirements | **Implemented baseline; review open** | Independently review requirement coverage and scope inheritance across case, supplier, installation and import line; test upload-to-fact provenance and human verification boundaries. |
| 4 | Exception management and audit trail | **Implemented baseline; review open** | Validate state transitions, permissions, immutable history, audit-chain failure behavior and tenant isolation with adversarial cases. |
| 5 | Application security | **Regression baseline green** | Remote CI dependency audit and security tests pass. Remaining: external security review, production secret/configuration review, shared rate limiting for multiple replicas, and real malware scanning before customer uploads. |
| 6 | Database operations and recovery | **Tooling/tests present; recovery drill open** | Execute backup/restore and integrity validation on a separate environment; test rollback and document measured recovery steps. Unit tests alone are not an off-host recovery drill. |
| 7 | Demo UX and regression | **Baseline regression green; usability review open** | Validate full demo journeys with realistic synthetic cases, accessibility/keyboard flow, error states, and product usability review. |
| 8 | Agent workflow and source retrieval | **Implemented baseline; source corpus incomplete** | Confirm complete source corpus, retrieval citations/page hashes, agent-message chain, bounded model data, prompt-injection behavior and no automatic consequential actions. |
| 9 | Documentation and release governance | **Core docs published; final freeze open** | Keep README, release status, checklist, source hierarchy and Antigravity brief consistent with latest HEAD; freeze version only after gates pass. |
| 10 | Deployment and operations | **BLOCKED** | Do not deploy until CI is green at HEAD, legal source gate passes, production secrets and configuration are reviewed, health/readiness and migration plans are checked, and a rollback path is ready. |
| 11 | Network-enabled closeout and independent verification | **Prepared; not executed** | Acquire official sources, run external dependency and host checks, deploy only after gates are satisfied, then have Antigravity independently review the exact commit, test results, security boundaries, source reconciliation and deployed behavior. |

## Current verified evidence

- GitHub Actions run 37979224155 passed on commit 3fbc1879157b365c62710850433c4e16eb69c6a6: dependency audit, Python compilation, and all nine regression suites.
- GitHub Actions run 37979224153 fetched all five official EUR-Lex HTML sources (HTTP 200) and extracted source-located table rows without approval. Artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979224153/artifacts/11641070061 (SHA-256 81238194daa0df176de8d40b69cc8ad0ee64f04bad513d0c3407b0c2ac0621d6; expires 16 October 2026).
- Extraction counts are preliminary only: defaults consolidated 13,633 rows; defaults base 13,646; correction act 13,521; benchmark source 63; emissions methodology 604. These are raw HTML table rows, not canonical legal-record counts. Completeness, annex mapping, route semantics and cell extraction require review.
- The CI dependency audit reported no known vulnerabilities in the published dependency environment. This is not a security certification.
- Regression coverage includes unit, HTTP integration, security, regulatory import guard, agent workflow, demo rendering, legal parser/rules, source governance, and database recovery utilities.
- Workbook-based parser tests are skipped in GitHub because source workbooks are intentionally not committed. They must be run in the controlled local workspace and their evidence retained.
- Public source publication is partial with respect to the local workspace and source inputs. No source workbook, confidential supplier data, or row-level reconciliation export is included.
- The legal pipeline contains 14,627 staged records. Seven curated canonical-source spot checks passed; 14,620 records remain pending canonical reconciliation. Pending means unreviewed against canonical binding data, not necessarily wrong.
- No canonical regulatory dataset has been promoted. No production deployment, independent Antigravity verification, or client outreach is authorized.

## Closeout order for tonight

1. Keep CI green at HEAD after documentation and source changes.
2. Complete the network-dependent acquisition attempt and record source hashes/errors without promoting incomplete data.
3. Run source-independent checks, security/configuration review, and recovery tooling tests.
4. Publish an accurate release record and verification brief.
5. Do not bypass Sprint 1 or Sprint 10 gates merely to claim all sprints complete. If binding source reconciliation remains incomplete, close the night with the engineering candidate tested and the regulatory/deployment gates explicitly blocked.

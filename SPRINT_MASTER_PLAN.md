# CBEOS Sprint Master Plan and Closeout

Updated: 10 October 2026 (IST). This is a live engineering record, not a release certificate.

## Release principle

A sprint is not “done” because code exists. Each sprint requires its deliverable, regression evidence, operational checks where applicable, and explicit blockers. The public branch is an engineering candidate. The regulatory dataset remains unapproved, and production deployment is not authorized.

## Sprint ledger

| Sprint | Workstream | Current state | Exit gate / remaining work |
|---|---|---|---|
| 1 | Legal source acquisition and reconciliation | **Machine row-level reconciliation complete; legal review open** | All 14,627 staged rows match extracted EUR-Lex table cells: Annex I 12,540/12,540; Annex IV 283/283; benchmarks 1,804/1,804. Machine comparison found no mismatch or ambiguity. Qualified review of source completeness, nested-table semantics, effective dates, fallback rules and routes remains mandatory before approving an immutable dataset version. |
| 2 | Calculation rules and traceability | **Golden arithmetic baseline passes; broader review open** | Six independent arithmetic/selector cases pass, including total-field handling and route-specific benchmarks. Broader liability, precursor, free-allocation and effective-date rules still need review against approved source data. |
| 3 | Evidence graph and scoped requirements | **Implemented baseline; review open** | Independently review requirement coverage and scope inheritance across case, supplier, installation and import line; test upload-to-fact provenance and human verification boundaries. |
| 4 | Exception management and audit trail | **Implemented baseline; review open** | Validate state transitions, permissions, immutable history, audit-chain failure behavior and tenant isolation with adversarial cases. |
| 5 | Application security | **Regression baseline green** | Remote CI dependency audit and security tests pass. Remaining: external security review, production secret/configuration review, shared rate limiting for multiple replicas, and real malware scanning before customer uploads. |
| 6 | Database operations and recovery | **Tooling/tests present; recovery drill open** | Execute backup/restore and integrity validation on a separate environment; test rollback and document measured recovery steps. Unit tests alone are not an off-host recovery drill. |
| 7 | Demo UX and regression | **Baseline regression green; usability review open** | Validate full demo journeys with realistic synthetic cases, accessibility/keyboard flow, error states, and product usability review. |
| 8 | Agent workflow and source retrieval | **Implemented baseline; source corpus incomplete** | Confirm complete source corpus, retrieval citations/page hashes, agent-message chain, bounded model data, prompt-injection behavior and no automatic consequential actions. |
| 9 | Documentation and release governance | **Core docs published; final freeze open** | Keep README, release status, checklist, source hierarchy and Antigravity brief consistent with latest HEAD; freeze version only after gates pass. |
| 10 | Deployment and operations | **BLOCKED** | Do not deploy until CI is green at HEAD, legal source gate passes, production secrets and configuration are reviewed, health/readiness and migration plans are checked, and a rollback path is ready. |
| 11 | Network-enabled closeout and independent verification | **Acquisition and machine reconciliation executed; Antigravity review open** | Official-source archive acquired and hash-verified; all 14,627 staged rows matched extracted source cells; six golden cases pass. Qualified legal/source review and Antigravity verification remain open. Deployment stays gated. |

## Current verified evidence

- GitHub Actions run 37979407230 passed on commit 7980649e9288c57d1990c2f6f106b056d3d162ce: dependency audit, Python compilation, and all ten regression suites, including source-table extraction tests.
- GitHub Actions run 37979394337 fetched all five official EUR-Lex HTML sources (HTTP 200) and extracted source-located table rows without approval. Artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337/artifacts/11641145249 (SHA-256 b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862; expires 16 October 2026).
- Extraction counts are preliminary only: defaults consolidated 13,633 rows; defaults base 13,646; correction act 13,521; benchmark source 654; emissions methodology 846. These are raw HTML table rows, not canonical legal-record counts. Completeness, annex mapping, route semantics and cell extraction require review.
- The CI dependency audit reported no known vulnerabilities in the published dependency environment. This is not a security certification.
- Regression coverage includes unit, HTTP integration, security, regulatory import guard, agent workflow, demo rendering, legal parser/rules, source governance, and database recovery utilities.
- Workbook-based parser tests are skipped in GitHub because source workbooks are intentionally not committed. They must be run in the controlled local workspace and their evidence retained.
- Public source publication is partial with respect to the local workspace and source inputs. No source workbook, confidential supplier data, or row-level reconciliation export is included.
- The legal pipeline now has a full machine comparison of 14,627 staged records against extracted EUR-Lex cells: Annex I 12,540; Annex IV 283; benchmarks 1,804; zero mismatches or ambiguous matches. These are `EXTRACTED_UNREVIEWED` matches, not legal approval.
- Six independent golden calculation cases pass. The runtime now has a tested helper for total-field markup and rejects invalid/non-finite values. No canonical regulatory dataset has been promoted. No production deployment, off-host recovery drill, independent Antigravity verification, or client outreach is authorized.

## Closeout order for tonight

1. Keep CI green at HEAD after the reconciler, runtime helper, golden cases and documentation changes.
2. Acquire the archive, verify its hash, and complete row-level machine reconciliation without promoting data.
3. Run source-independent checks, security/configuration review, and recovery tooling tests.
4. Publish an accurate release record and verification brief.
5. Do not bypass legal review or Sprint 10 gates merely to claim all sprints complete. The engineering candidate is tested; legal approval, Antigravity review and production release remain blocked.

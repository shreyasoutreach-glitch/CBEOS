# Antigravity Independent Verification Brief

## Objective

Independently challenge the exact CBEOS release candidate identified by commit SHA, release tag, ZIP SHA-256 and test report. Do not assume the author's report is correct.

## Required procedure

1. Record commit SHA, package SHA-256, runtime versions and operating system.
2. Read README, sprint status, architecture, threat model, data governance, release notes and known limitations.
3. Recreate the environment from documented steps. Run all tests from a clean checkout and preserve complete logs.
4. Inspect every calculation path and trace values to authoritative legal sources, effective dates, units, route/column semantics and approved dataset version.
5. Probe missing/dash/N/A/parent rows, unknown country/code, duplicate keys, ambiguous route, fallback candidates, rounding, stale versions, malformed inputs and unsupported cases.
6. Probe tenant isolation, authorization, upload handling, prompt injection, secret handling, logging, export permissions, idempotency, retries, provider outage, backup restoration and rollback where those features exist.
7. Check UI states, keyboard accessibility, error messages, export provenance and that demo data is clearly synthetic.
8. Search for credentials, secrets, unsafe defaults, misleading legal claims, dead code and untested privileged operations.
9. For each finding, provide severity, exact file/line or reproduction, expected vs actual result, impact, minimal fix and regression test.
10. Do not modify production, promote legal data, send outreach, or make external legal claims. Do not silently fix and hide findings; preserve an auditable finding list.

## Output format

- Executive disposition: PASS / PASS WITH LIMITATIONS / FAIL.
- Environment and exact versions.
- Test commands, exit codes and log paths.
- Findings sorted by severity with reproducible steps.
- Calculation/source coverage matrix and unsupported areas.
- Security/privacy review scope and limitations.
- Fixes made, changed files, added regression tests and rerun results.
- Remaining blockers and explicit go/no-go recommendation.



## Current network-source artifact (10 October 2026)

- Acquisition workflow: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337
- Verified unreviewed source artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337/artifacts/11641145249
- Artifact SHA-256 recorded by GitHub: b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862. Verify the latest run's artifact digest independently; do not assume digests remain identical across acquisition timestamps.
- The artifact contains five official EUR-Lex HTML pages, parsed text, an acquisition manifest, and table-extraction JSONL rows. All are explicitly unreviewed/not approved. Source-file hashes from that artifact:

| Source file | SHA-256 |
|---|---|
| defaults_consolidated.html | bb7a38fd364249470b80535790cacbe28e0de30a466939e33dbadc001c398247 |
| defaults_base.html | 0dffca2443356946350983d5f7616b032780127185dffd1c6b7e91a882addb7d |
| defaults_correction.html | 754b3456caec30b8f6fae146805f9d7ddaeed2bdcf262e1d094043c4f8230d92 |
| benchmarks.html | 423a322e4def4b4bbcfd2a3c472e07417e32870dd76aed68008e4d7d42930cbf |
| emissions_methodology.html | 24c167d1088309d68d4fbec011c9bc5f2ee4d7246036943a8eaeab9bf99390bf |

- Latest unreviewed extraction counts: defaults consolidated 13,633 rows; defaults base 13,646; correction act 13,521; benchmarks 654; emissions methodology 846. These are raw HTML table rows, not canonical legal-record counts. They are discovery signals only. Validate nested tables, country/CN/route identities, annex labels, unit semantics, effective dates, and corrected rows.
- Artifact retention is seven days. Download it and preserve the archive digest and extracted file hashes in the independent report.

## Independence boundary

A green software test run does not prove legal correctness. Antigravity verification is not a legal opinion, regulator approval, accredited verifier opinion or independent penetration test unless the relevant qualified scope is separately commissioned and documented.

## Client-outcomes megasprint hand-off (10 October 2026)

- PR: https://github.com/shreyasoutreach-glitch/CBEOS/pull/1
- Branch: meg-sprint/client-outcome-closeout-2026-10-10
- Scope: outcome-first dashboard, sandbox boundary, guided navigation to cases/suppliers/exceptions/verification, tenant-derived action snapshot, dashboard regression assertions, corrected evidence status, and client demo runbook.
- Before review, record the exact PR head SHA from GitHub. Do not assume the main branch's prior green run validates this branch.
- Start with CLIENT_DEMO_RUNBOOK.md and MEGASPRINT_CLIENT_OUTCOMES.md. Test the synthetic operator journey and report dead ends, misleading status labels, untraceable claims, accessibility issues, broken routes and high-impact security defects.
- Important correction: the full 14,627-row legal source reconciliation is NOT VERIFIED AS EXECUTED from reproducible evidence available to this hand-off. Do not confirm it as complete. Inspect the reconciler, execute it against the actual source archive and original workbooks if those artifacts are available, preserve logs/output, and report exact coverage and limitations. Do not infer that all rows match.
- Golden arithmetic fixtures do not establish legal source provenance or complete regulatory correctness. No legal dataset is approved/promoted; do not enable live liability/filing reliance.
- Do not deploy, promote data, send client outreach, or silently hide findings. Deliver a severity-ranked finding register with reproduction steps, file/line, impact, minimal fix and regression test. Rerun affected tests after any fix.

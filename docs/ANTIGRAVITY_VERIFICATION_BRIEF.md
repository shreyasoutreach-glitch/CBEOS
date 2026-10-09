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
- Verified unreviewed source artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979224153/artifacts/11641070061
- Artifact SHA-256 recorded by GitHub for the earlier identical-size artifact: 81238194daa0df176de8d40b69cc8ad0ee64f04bad513d0c3407b0c2ac0621d6. Verify the latest run's artifact digest independently; do not assume digests remain identical across acquisition timestamps.
- The artifact contains five official EUR-Lex HTML pages, parsed text, an acquisition manifest with raw-file hashes, and table-extraction JSONL rows. All are explicitly unreviewed/not approved.
- Extraction row counts are discovery signals only. In particular, a low table-row count or high row count does not establish annex completeness or correct structure. Validate nested tables, country/CN/route identities, annex labels, unit semantics, effective dates, and corrected rows.
- Artifact retention is seven days. Download it and preserve the archive digest and extracted file hashes in the independent report.

## Independence boundary

A green software test run does not prove legal correctness. Antigravity verification is not a legal opinion, regulator approval, accredited verifier opinion or independent penetration test unless the relevant qualified scope is separately commissioned and documented.

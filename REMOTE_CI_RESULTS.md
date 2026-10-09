# Remote CI and source acquisition results

Updated: 10 October 2026 (IST).

## Current regression gate

Workflow: [CBEOS tests at HEAD](https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979549673)

- Dependency install: PASS.
- pip-audit: PASS, output “No known vulnerabilities found” for the published dependency environment.
- Python compilation: PASS.
- Regression runner: PASS, all ten suites pass.
- The current branch is an engineering candidate. A green CI run is not regulatory sign-off, a security certification, or production approval.

Ten suites cover unit behavior, HTTP integration, security, regulatory import/promotion guards, agent workflow, demo rendering, legal parser/rule guards, source-table extraction, source governance, and database backup/restore utilities. Two workbook-dependent parser tests are intentionally skipped in GitHub because raw source workbooks are not committed.

## Official source acquisition

Workflow: [Acquire official CBAM sources](https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337)

- All five official EUR-Lex HTML sources were retrieved with HTTP 200.
- The extraction script produced source-located HTML table rows and a manifest. All rows remain EXTRACTED_UNREVIEWED / NOT_APPROVED.
- Artifact: [Download the unreviewed source archive](https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337/artifacts/11641145249)
- Artifact SHA-256: b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862
- Artifact expires 16 October 2026.

Extracted row counts are raw HTML table rows, not canonical legal-record counts. They do not establish complete annex extraction, correct row mapping, or legal validity. Independently verify source hash, annex/table identity, country, full CN/TARIC code, route, units, effective date, fallback behavior and correction-sensitive rows.

## Remaining release blockers

- 14,627 staged workbook records exist; only seven curated binding-source spot checks are confirmed. 14,620 rows remain pending canonical reconciliation. “Pending” means not reconciled, not necessarily incorrect.
- The supplied legal workbooks are not committed to this public repository. Run workbook-dependent staging/reconciliation in the controlled workspace.
- No canonical regulatory dataset has been promoted.
- No production deployment, off-host recovery drill, independent Antigravity verification, or client outreach has occurred.

**Go/no-go:** NO-GO for production or legal/financial reliance. GO for continued engineering and independent review of the exact published commit and unreviewed source artifact.

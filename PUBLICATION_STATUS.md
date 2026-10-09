# GitHub publication status

Updated 10 October 2026 (IST).

## Current state

The public repository contains the app runtime modules, regression tests, the acquired-source reconciliation tool, golden cases, governance docs, and GitHub Actions workflows. The complete local engineering workspace, raw workbook inputs, and full row-level CSV exports are not published, so this is still a partial source publication.

- Repository: https://github.com/shreyasoutreach-glitch/CBEOS
- Last previously confirmed green regression run: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979670408. New runtime and reconciliation changes have passed the local full application test suite; remote CI for the current HEAD must be checked before release.
- Latest EUR-Lex acquisition/extraction run: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337
- Unreviewed source artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337/artifacts/11641145249
- Artifact SHA-256: b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862. Retention expires 16 October 2026.

## Regulatory boundary

Five official EUR-Lex HTML sources were retrieved with HTTP 200 and table rows extracted with source file/hash, table number and row number. This is raw source acquisition, not legal interpretation or canonical dataset approval. Extracted HTML row counts are not legal-record counts and do not prove complete annex coverage.

The staged workbook pipeline contains 14,627 records. A row-level machine comparison now matches Annex I defaults (12,540), Annex IV precursor defaults (283), and benchmark rows including continuations (1,804) to extracted EUR-Lex table cells, with zero mismatches or ambiguous keys. Summary: https://github.com/shreyasoutreach-glitch/CBEOS/blob/main/staging/output/acquired_source_reconciliation_summary.json. Six independent golden arithmetic/selector cases pass: https://github.com/shreyasoutreach-glitch/CBEOS/blob/main/staging/output/golden_calculation_review_report.json. The extracted source remains EXTRACTED_UNREVIEWED; machine matching is not legal sign-off, and no legal dataset has been promoted.

## Release decision

- Production deployment: **NO-GO**
- Live legal/financial reliance: **NO-GO**
- Continued engineering and independent review: **GO**

Do not deploy until the current HEAD has a green remote CI run, full legal source reconciliation is independently reviewed, golden calculation cases pass against an approved immutable dataset, production configuration and secrets are reviewed, off-host recovery is demonstrated, and Antigravity independently verifies the exact commit and artifact.

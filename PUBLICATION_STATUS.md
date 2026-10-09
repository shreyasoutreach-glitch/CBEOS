# GitHub publication status

Updated 10 October 2026 (IST).

## Current state

The public repository contains the app runtime modules, regression tests, regulatory staging/source acquisition tools, governance docs, and two GitHub Actions workflows. The complete local engineering workspace and raw workbook inputs are not published, so this is still a partial source publication.

- Repository: https://github.com/shreyasoutreach-glitch/CBEOS
- Latest confirmed green regression run before the latest documentation-only commits: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979549673
- That run passed dependency audit, Python compilation, and all ten regression suites.
- Latest EUR-Lex acquisition/extraction run: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337
- Unreviewed source artifact: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337/artifacts/11641145249
- Artifact SHA-256: b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862. Retention expires 16 October 2026.

## Regulatory boundary

Five official EUR-Lex HTML sources were retrieved with HTTP 200 and table rows extracted with source file/hash, table number and row number. This is raw source acquisition, not legal interpretation or canonical dataset approval. Extracted HTML row counts are not legal-record counts and do not prove complete annex coverage.

The staged workbook pipeline contains 14,627 records. Seven curated binding-source spot checks passed; 14,620 rows remain pending canonical reconciliation. “Pending” means not reconciled, not necessarily wrong. No legal dataset has been promoted.

## Release decision

- Production deployment: **NO-GO**
- Live legal/financial reliance: **NO-GO**
- Continued engineering and independent review: **GO**

Do not deploy until the current HEAD has a green remote CI run, full legal source reconciliation is independently reviewed, golden calculation cases pass against an approved immutable dataset, production configuration and secrets are reviewed, off-host recovery is demonstrated, and Antigravity independently verifies the exact commit and artifact.

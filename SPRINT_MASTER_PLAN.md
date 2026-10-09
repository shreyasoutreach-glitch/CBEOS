# CBEOS Sprint Master Plan

Updated: 10 October 2026 (IST). This is a live execution record, not a release certificate.

## North star

Sell a measurable operational outcome: supplier evidence recovered, conflicts surfaced, blocked import lines made actionable, and a traceable human-review package. The client-facing experience matters more than the volume of internal components. The sandbox must never imply regulatory approval or production readiness that has not been earned.

## Sprint ledger

| Sprint | Workstream | Evidence-based state | Remaining exit condition |
|---|---|---|---|
| 1 | Official source acquisition | **ACQUIRED / UNREVIEWED** | Preserve source hashes and locators; independently confirm completeness and meaning before any legal promotion. |
| 2 | Calculation rules and provenance | **ARITHMETIC FIXTURES ONLY** | Verify source-derived values and rules against an approved immutable dataset with independent golden cases. |
| 3 | Evidence graph and scoped requirements | **IMPLEMENTED BASELINE / REVIEW OPEN** | Adversarially test scope inheritance, document-to-fact provenance and human verification gates. |
| 4 | Exceptions and audit | **IMPLEMENTED BASELINE / REVIEW OPEN** | Verify transitions, permissions, immutable history, chain failure and tenant isolation. |
| 5 | Application security | **REMOTE REGRESSION BASELINE GREEN ON PRIOR MAIN HEAD** | Run CI on this branch; review deployment secrets/configuration, shared rate limiting, upload scanning and external security findings. |
| 6 | Database operations | **TOOLING/UNIT TESTS PRESENT; LIVE RECOVERY NOT PROVEN** | Execute and record a separate-environment backup/restore and rollback drill. |
| 7 | Product UX | **OUTCOME-FIRST DASHBOARD IMPLEMENTED ON MEGASPRINT BRANCH; CI PENDING** | Run tests and a full seeded synthetic journey, including empty/error states, accessibility and mobile layout. |
| 8 | Agent workflow | **PARTIAL / REVIEW OPEN** | Verify hand-offs, source citations, bounded inputs, prompt-injection resilience and no automatic consequential actions. |
| 9 | Release governance | **CORRECTION IN PROGRESS ON MEGASPRINT BRANCH** | Keep every status file aligned with actual evidence; freeze only after release gates pass. |
| 10 | Sandbox deployment | **NOT AUTHORIZED YET** | Pass branch CI, application/security review, config/secrets checks, health/readiness, recovery/rollback and deployed smoke tests. |
| 11 | Network/source verification | **ARCHIVE ACQUIRED; FULL ROW-LEVEL RECONCILIATION NOT VERIFIED AS EXECUTED; ANTIGRAVITY OPEN** | Reproduce reconciliation against actual artifact/workbooks, independently review legal/source semantics, then hand exact candidate to Antigravity. |
| 12 | Client outcomes megasprint | **IN PROGRESS** | Finish outcome-first workflow, honest status records, regression run, end-to-end demo, independent verification, sandbox deployment and a measured pilot package. |

## Evidence currently available

- Main branch's last known green remote CI run: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37981524399 on commit `c5f8a1d7534685db5fe8af07f86d1629681239f3`. It passed dependency audit, compilation and the published regression suites. It does **not** certify changes on this megasprint branch.
- Official EUR-Lex acquisition/extraction run: https://github.com/shreyasoutreach-glitch/CBEOS/actions/runs/37979394337. The downloaded artifact SHA-256 was reported as `b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862`; it remains unreviewed and has a stated expiry of 16 October 2026.
- The five-source HTML extraction produced preliminary raw table-row counts. These are not canonical legal-record counts and do not prove complete annex coverage.
- The published reconciliation script exists, but the available evidence does not establish that the full 14,627-row comparison was actually executed against the archived source artifact and original workbooks. Earlier status wording that claimed all rows matched was too strong and must not be repeated as fact.
- Seven curated binding-source spot checks were previously reported. They do not establish full coverage.
- No canonical legal dataset has been approved/promoted. No production deployment, independent Antigravity verification or client outreach is complete.

## Megasprint execution order

1. Outcome-first dashboard and guided navigation (implemented on branch; CI pending).
2. Truthful release records and reproducible test status (being corrected on branch).
3. Run dependency audit, compile and full regression suite at the exact branch HEAD; repair failures and rerun.
4. Exercise synthetic client journey end to end; verify source trace, supplier requests, exceptions, readiness, exports and audit.
5. Fix only demonstrable product defects and high-impact usability/security gaps; do not expand legal edge cases merely to make the checklist longer.
6. Run Antigravity independently against exact SHA and preserve its finding list.
7. Fix findings and rerun affected tests.
8. Deploy sandbox only after application/security gates pass; verify deployed login, key flows, health/readiness and rollback.
9. Prepare a pilot offer with measured operational results, explicit scope, synthetic-data demo, human-review boundary and no unsubstantiated ROI claims.

## Truth labels

Every closeout report must use **PASS**, **FAIL**, **BLOCKED**, or **NOT RUN**. Include exact commit SHA, command, exit code, logs/artifacts, defect and retest evidence. Never infer a pass from the existence of code or a green run on another commit.

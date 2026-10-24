# CBEOS Sprint Master Plan

Updated: 25 October 2026 (IST). This is a live execution record, not a release certificate.

## North star

Sell a measurable operational outcome: supplier evidence recovered, conflicts surfaced, blocked import lines made actionable, and a traceable human-review package. The client-facing experience matters more than the volume of internal components. The sandbox must never imply regulatory approval or production readiness that has not been earned.

## Hard execution rule: ship work, not repeated status reports

- No status-only work sessions. Each session must produce a tested product change, a verified customer-ready artifact, or a blocker proven with an attempted fallback. If none happened, say so once and change the execution method.
- Do not repeat unchanged blocker lists or restate the plan as progress. Carry forward only changed evidence, completed work, failed tests, and the next action.
- **Commercial acceptance target:** by 31 October 2026, CBEOS must be ready to sell as a narrowly scoped, human-reviewed service, not represented as production-ready SaaS.
- The minimum sellable package is: (1) a repeatable synthetic demo with source-traceable candidate facts in the exported workbook; (2) an operator runbook and explicit limits; (3) a fixed-scope offer, intake checklist, deliverables, review responsibilities and escalation path; (4) buyer-facing one-pager and personalized outreach draft; (5) clear separation between synthetic-demo readiness and permission to process real customer data.
- Real customer data stays out until tenant isolation, approved data transfer/storage, access controls, retention/deletion, backup/recovery and security review are verified. If these gates are still open, sell only a discovery/readiness engagement using synthetic examples and customer-described workflows.
- **Next status request is an acceptance review, not another planning session.** Report the demo/offer against the criteria above with evidence, blockers that actually changed, and a GO/NO-GO. Never label the service sellable merely because documentation exists.

## Sprint ledger

| Sprint | Workstream | Evidence-based state | Remaining exit condition |
|---|---|---|---|
| 1 | Official source acquisition | **ACQUIRED / UNREVIEWED** | Preserve source hashes and locators; independently confirm completeness and meaning before any legal promotion. |
| 2 | Calculation rules and provenance | **ARITHMETIC FIXTURES ONLY** | Verify source-derived values and rules against an approved immutable dataset with independent golden cases. |
| 3 | Evidence graph and scoped requirements | **IMPLEMENTED BASELINE / REVIEW OPEN** | Adversarially test scope inheritance, document-to-fact provenance and human verification gates. |
| 4 | Exceptions and audit | **IMPLEMENTED BASELINE / REVIEW OPEN** | Verify transitions, permissions, immutable history, chain failure and tenant isolation. |
| 5 | Application security | **REMOTE REGRESSION BASELINE GREEN ON PRIOR MAIN HEAD** | Run CI on this branch; review deployment secrets/configuration, shared rate limiting, upload scanning and external security findings. |
| 6 | Database operations | **TOOLING/UNIT TESTS PRESENT; LIVE RECOVERY NOT PROVEN** | Execute and record a separate-environment backup/restore and rollback drill. |
| 7 | Product UX | **OUTCOME-FIRST DASHBOARD IMPLEMENTED; REGRESSION SUITES PASS ON 9f8f361f21aa0c6ccff39e548835f890e7135325; FOLLOW-UP METADATA HEAD RETEST PENDING** | Run tests and a full seeded synthetic journey, including empty/error states, accessibility and mobile layout. |
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

1. Strengthen the seeded synthetic journey and exported source provenance; exact-head CI is the acceptance gate.
2. Truthful release records and reproducible test status (being corrected on branch).
3. Run dependency audit, compile and full regression suite at the exact branch HEAD; repair failures and rerun.
4. Exercise synthetic client journey end to end; verify source trace, supplier requests, exceptions, readiness, exports and audit.
5. Fix only demonstrable product defects and high-impact usability/security gaps; do not expand legal edge cases merely to make the checklist longer.
6. Run Antigravity independently against exact SHA and preserve its finding list.
7. Fix findings and rerun affected tests.
8. Deploy sandbox only after application/security gates pass; verify deployed login, key flows, health/readiness and rollback.
9. Close the sellable-service package: scoped offer, intake and data boundary, deliverables, human-review responsibilities, buyer one-pager and outreach draft. Use only measured claims; no invented ROI.

## Truth labels

Every closeout report must use **PASS**, **FAIL**, **BLOCKED**, or **NOT RUN**. Include exact commit SHA, command, exit code, logs/artifacts, defect and retest evidence. Never infer a pass from the existence of code or a green run on another commit.

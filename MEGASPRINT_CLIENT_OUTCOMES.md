# CBEOS Client Outcomes Megasprint

**Started:** 10 October 2026 (IST)  
**Branch:** `meg-sprint/client-outcome-closeout-2026-10-10`  
**Objective:** Deliver a navigable, outcome-first client demonstration of CBAM evidence operations. This is a product-closeout sprint, not a regulatory-data expansion sprint.

## The product promise

Help an importer or advisory team answer five operational questions in one place:

1. What is blocked, and what requires action now?
2. Which supplier or installation evidence is missing, conflicting, stale, or unverified?
3. Which import lines are affected, and can I trace the underlying source documents?
4. What work remains before a human verifier/reviewer can assess the case?
5. Can I export a transparent evidence and exception trail without presenting scenario estimates as legal liability?

CBEOS must demonstrate operational control and review readiness. It must not claim regulatory compliance, verified savings, legal liability, or successful filing without independent evidence.

## Sprint board

| Workstream | State | Deliverable / exit condition |
|---|---|---|
| 1. Client-first control tower | **Implemented on sprint branch; CI pending** | Dashboard opens with a clear sandbox boundary, four guided destinations (case, supplier, exception, verification), and an outcome snapshot derived from tenant workflow counts. Regression assertions added. |
| 2. Core operator journey | **Existing flows; verification pending** | Walk a synthetic case from import-line evidence through supplier follow-up, exception triage, provenance, readiness, declaration-package preview and audit. No dead ends or misleading success states. |
| 3. Evidence and exception truth | **Existing baseline; adversarial retest required** | Confirm every extracted fact links to a source document/location, conflicting evidence stays visible, unresolved cases stay blocked, and every consequential transition is audited. |
| 4. Sandbox integrity | **Partially implemented** | Clearly label synthetic/demo data; scenario calculations and illustrative values never masquerade as approved legal inputs. Keep consequential actions human-gated. |
| 5. Security and operational gates | **CI baseline exists; release gates open** | Green CI on exact candidate, config/secrets review, auth/tenant/CSRF/upload checks, health/readiness checks, safe migrations, backup/restore evidence and rollback path. |
| 6. Demo quality | **In progress** | Run all tests, exercise all key routes on a clean synthetic database, verify mobile layout and keyboard navigation, test empty/error states, inspect generated exports. |
| 7. Antigravity hand-off | **Brief exists; independent run not done** | Give Antigravity exact branch/commit, reproducible setup, tests, boundaries and required findings format. Preserve its findings and rerun tests after fixes. |
| 8. Client outcome package | **Not yet complete** | Create a concise demo narrative around evidence recovery, blocked-line reduction, exception resolution and review readiness. Only claim measured results from recorded runs; no invented ROI. |
| 9. Sandbox deployment | **Not authorized yet** | Deploy only after application/security gates pass. Sandbox-only, synthetic data, no live legal calculations or filing. Verify deployed health, login, guided journey, logs and rollback. |
| 10. Client outreach readiness | **Blocked by demo and independent review** | Prepare a tightly scoped pilot offer with clear deliverables, assumptions, exclusions, data handling and human-review boundary. Outreach is not authorized until the demo is verified. |

## Execution order

1. Complete the dashboard outcome/navigation change and its regression test.
2. Correct release and sprint records so they report only evidence actually collected.
3. Run compile, dependency audit and the full regression suite on the exact branch head; repair failures and rerun.
4. Test the seeded synthetic journey across dashboard, case, supplier, line trace, exception, verification, agent terminal, export and audit.
5. Review the app for dead-end links, unsafe defaults, misleading regulatory claims, broken empty states, missing source provenance and tenant/security regressions.
6. Produce the client demonstration script and Antigravity verification hand-off.
7. Run independent verification, fix findings, and rerun all affected tests.
8. Deploy the sandbox only when application/security gates pass; then smoke-test the deployed build and rollback procedure.
9. Mark client-pilot readiness only after the actual deployed journey and external review evidence are recorded.

## Hard boundaries

- The five acquired EUR-Lex HTML sources and their hashes are useful source-acquisition evidence only. Extracted table rows are not approved canonical records.
- **Full row-level legal reconciliation has not been independently verified as executed.** The repository's prior status text overstated this. Treat the reconciliation tool as prepared but execution unverified until the command is actually run against the real archived source artifact and source workbooks, with reproducible output.
- Golden arithmetic fixtures test arithmetic/selector behavior; they do not prove that every legal value, row, effective date or route is correct.
- No unapproved legal dataset may be promoted. No live CBAM liability calculation, filing, or customer reliance is authorized.
- A green CI run means the tested code passed those checks. It does not certify regulatory correctness, production security, or zero defects.
- Do not send confidential client/supplier data to optional model providers. Agents advise; humans own verification, approvals, and declarations.

## Completion report format

For every gate, report one of: **PASS**, **FAIL**, **BLOCKED**, or **NOT RUN**. Include exact commit SHA, command, exit code, artifact/log reference, defects found, fixes made, and retest evidence. Never replace missing evidence with an assumed PASS.

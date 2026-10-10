# CBEOS Client Demo Runbook

**Audience:** importer operations lead, trade/compliance manager, finance leader, or advisory partner.  
**Scenario:** synthetic importer portfolio only.  
**Purpose:** demonstrate operational outcomes and evidence traceability, not legal CBAM liability or filing.

## Opening: the business problem

Supplier declarations, invoices, packing lists and installation details arrive in different formats. Teams spend time chasing missing documents, resolving conflicting quantities, and explaining why an import line cannot yet be reviewed. CBEOS creates one traceable workflow across evidence, exceptions, supplier follow-up and human review.

## Five-minute guided walkthrough

### 1. Control tower: what needs action?

Open /. Point to blocked import lines, high-severity open exceptions, overdue supplier requests, the explicit sandbox boundary and the four workflow links.

Say: “These are operational workflow counts from this workspace. They are not proof of compliance, savings, or legal liability.”

### 2. Case workspace: locate the bottleneck

Open Cases, then the synthetic 2026 case. Show readiness, blocked lines, documents, open exceptions and the import-line table. Choose one blocked line and open its trace view.

Demonstrate the difference between a workflow being organized and a figure being legally approved. A blocked line is a useful operational result because the missing decision is visible and assignable.

### 3. Evidence: show the chain of custody

Open a document and its extracted facts. Trace each candidate fact to the source document and location/excerpt. Explain that extraction is a suggestion; a human reviewer owns verification. Conflicting or low-confidence evidence must remain visible, not be silently overwritten.

### 4. Supplier operations: make the next action obvious

Open Suppliers and a supplier record. Show request status, deadline/escalation and the installation/import lines affected. Show what evidence is missing or contradictory and the next action that would unblock review.

Do not claim an email was actually sent unless the application records real provider delivery. Demo requests are workflow records, not proof of external delivery.

### 5. Exceptions: turn uncertainty into a queue

Open Exceptions. Pick one high-priority issue and explain its source, affected scope, owner, current status and next human action. Show the available transition and audit trail. Do not resolve an exception merely to make the dashboard look green.

### 6. Verification and declaration preview: hand off responsibly

Open Verification, then the declaration-package preview for the case. Show readiness blockers and provenance. Explain that the package is a review artifact only. No filing is transmitted and no unapproved legal data is promoted.

### 7. Audit: prove what happened

Open Audit and show action history and chain-integrity status. Explain that a traceable record helps internal review and hand-off, while independent assurance is still required.

## Claims we may make

- The sandbox organizes supplier/import evidence into a traceable workflow.
- It surfaces configured evidence gaps, reconciliation conflicts and follow-up status.
- It supports a human-controlled review hand-off and audit trail.
- The demo can measure operational counts and time-to-resolution once a real pilot defines a baseline and records outcomes.

## Claims we must not make without new evidence

- “CBAM compliant”, “legally accurate”, “verified liability”, “filing-ready” as an assurance claim, or “zero bugs”.
- Quantified savings, reduced risk, time saved or ROI not measured in a documented pilot.
- That external supplier communications were delivered without provider evidence.
- That illustrative/default values are authoritative.
- That Antigravity or another independent reviewer approved a commit before a report exists.

## Acceptance checklist

- [ ] Demo starts from a clean synthetic database.
- [ ] All navigation links resolve and all key screens render.
- [ ] At least one blocked line and one exception can be traced to supporting records.
- [ ] Candidate facts, confidence and source locations are visible.
- [ ] No unresolved conflict is presented as resolved.
- [ ] Scenario calculations are clearly labelled and cannot be mistaken for approved legal liability.
- [ ] No real supplier/client data or credentials are present in the demo.
- [ ] Export/preview is generated and its provenance can be inspected.
- [ ] Audit chain verifies and the result is recorded.
- [ ] CI passes on the exact commit; deployed sandbox smoke test passes before sharing externally.

## Pilot outcome measurement

For a real, permissioned pilot, agree a baseline before work begins. Measure only what can be evidenced: time from evidence request to usable supplier response; number and age of blocked import lines; time to detect and resolve a conflicting document pair; evidence completeness at human-review hand-off; and unresolved exceptions at the agreed checkpoint.

Record sample size, observation window, exclusions and source logs. Do not extrapolate a small pilot into a universal performance guarantee.

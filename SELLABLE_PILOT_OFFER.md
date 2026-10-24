# CBEOS | CBAM Evidence Recovery Sprint

**Status:** Commercial offer draft; synthetic demo only until data-security gates are independently verified.  
**Initial wedge:** EU-facing steel importers and their trade/compliance advisers.  
**Delivery model:** Human-reviewed service supported by CBEOS, not autonomous compliance software.

## The offer

CBEOS helps an operations or trade-compliance team turn scattered supplier and import evidence into a structured review queue: what is present, what is missing, what conflicts, who needs to act, and what a human reviewer still needs to verify.

The service is designed to make evidence follow-up and review hand-off more organized. It does not certify CBAM compliance, determine legally authoritative liability, submit declarations, or replace a qualified verifier or adviser.

## Engagement options

### Option A: Evidence Readiness Review

**Use when customer-data handling has not yet been approved.**

- Walk through the buyer's current evidence workflow using a synthetic CBEOS demo and the buyer's verbal/process description only.
- Map the steps from supplier evidence request to internal review.
- Identify likely evidence hand-off gaps, ownership ambiguity and follow-up bottlenecks.
- Deliver a process map, prioritized readiness/gap list, proposed pilot scope and acceptance criteria.
- No customer files, personal data, supplier-confidential documents, credentials or live regulatory dataset are uploaded to CBEOS.

### Option B: Human-Reviewed Evidence Recovery Sprint

**Available only after written data-handling approval and verification of required security/infrastructure controls.**

- Scope: one customer account, one facility/product family, and 10–25 import lines.
- Duration: 10 business days after complete intake and access approval.
- Inputs: customer-authorized evidence and a named customer reviewer; only via an agreed, approved transfer channel.
- Deliverables:
  1. Source-linked evidence register with document identifier, source location/excerpt, extraction confidence and review status.
  2. Missing/conflicting evidence matrix mapped to affected lines.
  3. Exception register with severity, owner, next action and due-date fields.
  4. Supplier follow-up tracker and draft request wording.
  5. Human-review hand-off pack and a closeout readout of unresolved questions.
- Customer responsibilities: confirm scope, provide lawful/authorized records, nominate a reviewer, resolve interpretation questions, and approve all consequential decisions.
- Exclusions: legal opinion, assurance/certification, verified emissions or liability calculation, declaration filing, guaranteed savings, automatic supplier communication, and approval of regulatory source data.

## Acceptance criteria

The engagement is complete when the agreed scope has been processed and the buyer can inspect:
- which documents were received and their recorded fingerprints;
- candidate facts and their source locations/excerpts;
- unresolved evidence gaps and conflicts;
- assigned next actions and open exceptions;
- review status, audit trail and a clearly labelled hand-off pack.

A fact remains a candidate until a human reviewer verifies it. A missing record stays missing. A conflict is not silently resolved. Any unsupported or untested integration is disclosed.

## Commercial terms to validate

- **Initial pricing hypothesis for Option B:** ₹25,000–₹50,000 per scoped sprint. This is an unvalidated test range, not established willingness to pay.
- Option A pricing, payment terms, taxes, cancellation and any data-processing agreement must be agreed before a paid engagement.
- No ROI, time-saved or risk-reduction claim will be made without a documented baseline and observed outcome.

## Readiness gate before accepting customer data

Do not accept live customer evidence until the owner has approved the transfer method and the team has verified tenant isolation, least-privilege access, private storage, deletion/retention handling, backup/restore, logging/secret safety and incident/escalation procedures. A green synthetic CI run or live sandbox does not substitute for these checks.

## Buyer-facing positioning

**Headline:** Turn scattered CBAM evidence into a reviewable action queue.

**Short pitch:** CBEOS helps steel import operations teams organize supplier documents, surface missing or conflicting evidence, assign follow-up, and hand a source-linked evidence pack to a human reviewer. Start with a synthetic walkthrough and a bounded workflow review. No automated compliance claims, and no customer files are needed for the initial readiness review.

## Discovery questions

1. Which evidence items take the most time to collect or reconcile?
2. Where do supplier declarations, invoices, shipment records and installation data currently live?
3. How are missing or conflicting items assigned and chased today?
4. Who signs off the evidence before a qualified reviewer or adviser uses it?
5. What would make a 10-day, 10–25-line evidence recovery engagement useful enough to pay for?
6. What data-handling, security or procurement requirements must be met before any records can be shared?

## Outreach draft (do not send without recipient and message approval)

Subject: Reducing evidence-chasing for CBAM steel imports

Hi [Name],

I'm working on CBEOS, a human-reviewed workflow for organizing CBAM-related supplier and import evidence. It is designed to make missing documents, conflicting records and next actions easier to see, with each candidate fact linked back to its source.

I'm speaking with teams handling EU-facing steel imports to understand where evidence collection and review hand-offs create the most manual work. I can show a short synthetic-data walkthrough; no confidential documents are needed.

Would a 15-minute conversation next week be useful to compare your current process with the workflow we're building?

Best,  
[Your name]

## Internal go/no-go

- [ ] Synthetic end-to-end demo passes exact-head CI.
- [ ] Exported candidate facts preserve document ID, SHA-256, source location, excerpt, confidence and candidate status.
- [ ] Operator runbook matches actual behavior.
- [ ] Option A is ready to offer without receiving customer files.
- [ ] Option B remains gated until data-handling and security checks are verified.
- [ ] Claims and pricing are presented as hypotheses where evidence is absent.

# CBEOS Commercial Wedge: Evidence Recovery, Not Another CBAM Calculator

**Decision:** Do not position CBEOS as a generic CBAM calculator, compliance certification tool, or Registry filing product. The initial wedge is **evidence recovery and review operations** for Indian manufacturers that need to answer EU customers' installation-level emissions and traceability requests.

## Why this wedge exists now

The European Commission says the definitive CBAM regime applies from 1 January 2026. Its 2026 guidance is aimed in part at non-EU installation operators, authorised declarants and verifiers. Actual emissions data must be supported and verified at installation level; importers can otherwise use the applicable default values. The Commission's current timetable points to first verification reports from January 2027 and the first annual declaration for 2026 imports by 30 September 2027.

Primary sources:
- [CBAM definitive regime](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-definitive-regime_en)
- [CBAM verification](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-verification_en)
- [Commission's August 2026 guidance package](https://taxation-customs.ec.europa.eu/news/european-commission-publishes-series-guidance-documents-support-cbam-implementation-definitive-2026-08-14_en)
- [CBAM legislation and corrected default-value references](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en)

This is a workflow thesis, not proof of willingness to pay. The regulatory timetable creates a reason to act; customer interviews and paid pilots must prove the commercial pain.

## The narrow initial customer

**Ideal customer profile (hypothesis):**
- Indian steel or aluminium manufacturer exporting covered goods to EU customers.
- One to three installations or production routes in the first engagement.
- EU customer/importer is asking for installation-specific emissions evidence, methodology, activity data, or verifier support.
- Data is scattered across spreadsheets, Tally/ERP exports, supplier emails and PDFs.
- A finance, export, quality, sustainability or compliance lead is personally coordinating follow-ups.

**Economic buyer:** CFO/finance head, head of exports, plant controller, or sustainability/compliance lead.  
**Daily user:** export operations, quality, plant finance, sustainability, or a consultant coordinating evidence.  
**Channel hypothesis:** CBAM consultants, accredited verifier networks, export associations, and ERP/Tally implementation partners. These are discovery channels, not confirmed partnerships.

Do not start by targeting every CBAM sector. Start with steel, where the team can learn one evidence taxonomy and repeat it.

## What we sell

### Evidence Recovery Sprint

A bounded, human-reviewed service using CBEOS as the workflow engine.

- **Scope hypothesis:** one installation/product family, 10–25 import lines, one reporting period.
- **Duration hypothesis:** 10 business days after receiving agreed inputs.
- **Price hypothesis:** ₹25,000–₹50,000 fixed fee for the first paid pilot. This is not validated market pricing.
- **Inputs:** customer-approved import-line register, available supplier/installation records and redacted or synthetic documents during technical evaluation.
- **Deliverables:** source-linked evidence register, prioritized gaps/conflicts, owner-assigned supplier follow-ups, open-exception queue, document register, review-package preview and a measured before/after workflow report.
- **Human responsibility:** customer and qualified advisers validate facts, methods, legal interpretation and any submission. CBEOS does not certify compliance or submit to the CBAM Registry.

The first sale is not “buy our AI.” It is “let us measure how quickly your team can close a defined set of evidence gaps, and show exactly what remains unresolved.”

## Why CBEOS instead of another calculator?

The market already has products advertising CBAM calculation, reporting, and ERP/Tally integrations. We should not compete feature-for-feature before proving an advantage. CBEOS should differentiate on the **operational evidence trail**:

1. Every candidate fact is linked to its document and available source context.
2. Missing evidence and conflicts become owned exceptions with next actions.
3. Supplier follow-up, evidence status and reviewer decisions are visible in one case workflow.
4. The recovery workbook hands unresolved work to a human reviewer instead of presenting a false green “compliant” badge.
5. The pilot measures process outcomes rather than inventing savings or regulatory certainty.

Public competitor positioning to validate in discovery:
- [NetZerra](https://www.netzerra.com/) markets a CBAM platform for Indian manufacturers with native Tally integration.
- Search and compare alternatives on evidence lineage, exception ownership, installation-level data, human review and buyer workflow. Do not repeat competitors' marketing claims as independently verified facts.

## What the buyer must receive to justify paying

A pilot must produce all of the following, not merely a dashboard:
- A usable, tenant-scoped recovery workbook.
- Each gap has a reason, owner, next action and status.
- Each material fact shows its source or is explicitly marked unsupported.
- Conflicting and missing information stays unresolved until a human decides.
- An audit trail makes changes and approvals inspectable.
- A closeout report compares baseline with final measures.

**Pilot measures:** staff hours spent chasing/reconciling evidence; elapsed business days; evidence completeness by agreed checklist; open high-priority exceptions; supplier response rate; reviewer rework; number of unsupported facts caught before handoff. Establish baseline before the sprint. Report results even if they are disappointing.

## Objections to test

| Buyer objection | What we need to prove |
|---|---|
| “Our consultant already does this.” | CBEOS reduces evidence coordination effort or improves traceability without displacing the consultant's legal role. |
| “We already use Tally/ERP.” | The gap is not ledger entry alone; it is linking installation, shipment, method and supporting documents to review actions. |
| “We can use spreadsheets.” | The same scoped pilot must show fewer missed follow-ups, faster closure or less reviewer rework. If it cannot, do not sell software. |
| “Will this guarantee CBAM compliance or lower certificate costs?” | No. It organizes evidence and workflow; legal interpretation, verified emissions and filing remain with qualified parties. |
| “Can we upload our real supplier documents today?” | Not until database connectivity, durable private storage, access controls, scanning, retention/deletion and recovery are independently verified. |

## Sales sequence

1. Build a list of 50 named Indian steel exporters with evidence of EU exposure, then manually qualify each account. Do not buy or scrape private contact data.
2. Contact the export/finance/compliance owner with one specific question about supplier evidence collection and verifier preparation.
3. Offer a 20-minute workflow diagnosis, not a generic product demo.
4. Map one recent evidence request from EU customer to source files, follow-ups and final review.
5. If pain is confirmed, offer a written, bounded paid pilot with agreed data handling and success measures.
6. Ask for permission to use only anonymized outcome metrics as a case study.
7. Do not automate bulk email sending until contact provenance, opt-out handling, sender identity, rate limits and provider delivery tracking are implemented.

## Go / no-go gates

- **Discovery gate:** 15 qualified conversations. If fewer than 5 describe recurring, costly evidence coordination pain, revisit the ICP.
- **Paid-pilot gate:** 3 written proposals and at least 1 paid pilot. If nobody pays, revise the offer before adding features.
- **Outcome gate:** report baseline and closeout honestly. Continue only if the buyer confirms material workflow value and agrees to a reference or repeat engagement.
- **Production gate:** no live customer data until the PostgreSQL connection, durable private object storage, secrets, tenant isolation, backups/restore, upload scanning, independent security review and qualified regulatory-data review pass.
- **Regulatory gate:** no authoritative liability output until the corrected source dataset, effective dates, route/fallback semantics and golden cases are approved by a qualified reviewer.

## Current engineering boundary

The dedicated CBEOS Supabase project now has the 35-table PostgreSQL schema, RLS enabled on all 35 application tables, 15 tenant-relationship triggers and two agent-run integrity triggers. The automatic RLS helper is no longer executable by anonymous or authenticated API roles.

The PostgreSQL compatibility layer and regression tests are in the repository, but **Render is not yet connected to PostgreSQL**: a server-side database login/connection secret has not been provisioned. The deployed Render service remains a free sandbox, and private durable object storage is not configured. This is not production-ready and must not process live customer documents. Do not claim otherwise in sales materials.

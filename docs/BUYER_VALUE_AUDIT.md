# CBEOS buyer-value audit: would a customer pay?

**Review date:** 11 October 2026  
**Decision standard:** a buyer pays for a business outcome, not the number of screens, agents, or lines of code.

## Buyer and buying moment

The most credible initial buyer is a CBAM advisory / trade-compliance consultancy or a mid-market EU importer that has enough covered imports and supplier relationships to make evidence collection painful. The product should start with one tightly scoped workflow: recover and organize evidence for one account/facility/product family, covering roughly 10–25 import lines in a 10-business-day, human-reviewed sprint.

The urgency is real but not universal. The definitive regime began on 1 January 2026, the first annual declaration for 2026 imports is due by 30 September 2027, and actual emissions need verification at installation level. Small importers under the applicable 50-tonne threshold may not be buyers at all. See the [European Commission definitive-regime page](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-definitive-regime_en), [verification guidance](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-verification_en), and [legislation and guidance](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en).

## Iteration 1: would I buy the current product as SaaS?

**No.**

Reasons:
1. It is an engineering sandbox, not a production system approved for confidential supplier or customer documents.
2. The app does not yet prove a reduction in the time from missing evidence to resolved evidence. Workflow counts are not ROI.
3. Intake and data reconciliation still require substantial human setup. No verified ERP/customs-system integration has been demonstrated.
4. The current experience is broad control-tower software. A buyer cannot immediately see a fixed deliverable, its acceptance criteria, or the person responsible for the next action.
5. The market already has CBAM products for importer workflows, supplier evidence, and data APIs. A generic dashboard is not a defensible wedge. A spreadsheet may also be sufficient for a low-volume importer.

### Fix shipped in this iteration

Added an authenticated, tenant-scoped **Recovery Workbook (XLSX)** download to each case. It creates seven handoff sheets:
- Read Me & Summary
- Import Lines
- Evidence Gaps
- Open Exceptions
- Supplier Follow-up
- Document Register
- Pilot Measurement, a blank baseline-versus-result worksheet for staff hours, elapsed days, open gaps, open exceptions, supplier response rate and reviewer rework.

The gap and exception sheets now include a suggested owner role and a category-specific next action. The pilot worksheet deliberately does not invent savings; baseline and result values must be measured. The workbook escapes formula-like untrusted strings, excludes raw extracted document text and credentials, and states that it is an operational handoff, not a legal opinion or compliance certificate. Unit and HTTP journey tests are included in CI.

This is a better deliverable, not yet proof of customer willingness to pay.

## Iteration 2: would I buy it after the workbook fix?

**Still no, not as an unattended SaaS subscription.**

The workbook makes the output easier to hand to a team, but it cannot create evidence that a supplier has not provided. Nor does it prove that requests were delivered, responses received, data persisted safely, or that a customer saved enough staff time to justify a recurring fee. The current Render service uses sandbox mode, SQLite-specific persistence and local filesystem uploads. Production mode must remain blocked until real PostgreSQL and durable object storage are implemented and tested, backups are restored in a drill, retention/deletion is enforced, malware scanning and security review are evidenced, and live integration checks pass.

### Commercial correction

Sell the **service outcome first**, not the prototype as a finished SaaS product:
- **Offer hypothesis:** CBAM Evidence Recovery Sprint, human-reviewed.
- **Scope:** one account/facility/product family, 10–25 import lines.
- **Turnaround target:** 10 business days after complete intake.
- **Deliverables:** source register, evidence-gap matrix, reconciliation log, supplier follow-up tracker, exception register, and handover workbook.
- **Price to test, not claim:** ₹25,000–₹50,000 fixed fee.
- **Do not promise:** authoritative liability, legal compliance certification, guaranteed savings, registry filing, or that all evidence will be obtained.

For now, the pilot must use synthetic or explicitly approved low-risk data until the production data controls are complete. A real paid pilot should not be offered for live confidential files on the current sandbox.

## Iteration 3: what would make me say yes?

I would consider paying for a narrowly scoped service only after these conditions are demonstrated, not merely promised:

1. **Buyer proof:** at least three qualified discovery conversations confirm the same painful workflow; at least one buyer signs a paid pilot at a tested price.
2. **Measured outcome:** capture baseline staff hours and elapsed days; compare them with hours, elapsed time, gaps resolved, supplier response rate, and reviewer rework after the sprint.
3. **Traceability:** every material field in the handoff links to a source record, an owner, a status, and an explicit unresolved question where evidence is insufficient.
4. **Operational closure:** supplier messages are sent only with approval; delivery and response states are verified rather than inferred from an API's HTTP 200.
5. **Data safety:** actual durable database and object-storage implementations, tested tenant isolation, backup restore, deletion/retention, malware scanning, secrets handling, and independent security review.
6. **Regulatory governance:** legal-source and effective-date review signed off by a qualified reviewer; machine row matching remains distinct from legal approval; unapproved datasets cannot drive customer-facing liability conclusions.
7. **Repeatability:** a second pilot can be delivered with less operator effort without lowering evidence quality.

## Stop conditions

Do not switch the service to production mode or ingest confidential customer data because the workbook looks polished or CI is green. Do not call a suggested action an automated resolution. Do not quote time saved until measured. Do not turn a pilot price hypothesis into a claim that the market has validated willingness to pay.

## Competitive context reviewed

The Commission publishes the binding legal acts and information-only workbooks. Public market comparisons describe existing providers covering importer compliance, supplier data, customs data, and emissions APIs; at least one comparator lists plans from approximately €99/month and another from about €1,990/year. Those are competitor-published price points, not proof that CBEOS is equivalent or that customers will pay CBEOS. See the Commission's [CBAM legislation and guidance](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en) and the third-party [2026 CBAM software comparison](https://cbamdata.eu/blog/cbam-software).

## Current honest verdict

- **Buy CBEOS as production SaaS today? No.**
- **Pay for a narrowly scoped, human-reviewed evidence recovery service? Plausible, unvalidated.**
- **What changes the answer?** Secure the data path, demonstrate the end-to-end workflow, measure the result, and obtain a paid pilot. The next buyer interview and pilot data, not more features for their own sake, determine whether to keep investing.

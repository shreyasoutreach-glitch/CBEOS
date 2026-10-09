# Regulatory Source Hierarchy and Promotion Gate

## Authority order

1. Binding EU legislation published in the Official Journal / EUR-Lex, including the act's applicable annexes.
2. Consolidated binding text where its status and consolidation date are explicit; verify against the act when discrepancies matter.
3. Commission implementation guidance and Registry instructions, for operational interpretation only.
4. Commission informational workbooks, portals, FAQs and supporting spreadsheets. Useful for discovery and reconciliation, not legally binding where the underlying act says otherwise.
5. Secondary commentary and vendor summaries. Use only to locate the primary source, not to approve values.
6. Internal assumptions and demonstrators. Must be explicitly labelled illustrative and must never silently become canonical regulatory data.

## Current correction-sensitive CBAM sources

- Commission Implementing Regulation (EU) 2026/1740: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1740
  Replaces Annexes I and IV of Regulation 2025/2621 in full and applies retrospectively from 1 January 2026.
- Commission Implementing Regulation (EU) 2025/2621: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2621
- Consolidated default-values act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02025R2621-20260101
- Commission Implementing Regulation (EU) 2025/2620 (CBAM benchmarks): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2620
- Commission Implementing Regulation (EU) 2025/2547 (emissions methodology): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2547

## Required reconciliation controls

- Hash-pin the raw official source and record acquisition time, effective date, parser version and canonical record count.
- Preserve original raw strings and parsed values separately, including blank, dash, parent rows, continuation rows, decimal commas, country labels, CN/TARIC code length and production-route indicators.
- Key on the binding identity tuple: legislation/version, annex, country/territory, CN/TARIC code, route where applicable and effective date. Never join only on a truncated prefix if a more specific legal row is available.
- Do not infer zero from a dash or missing value. Do not combine informational direct/indirect emissions when the binding annex specifies a separate total-emissions field.
- Recalculate default-value mark-ups separately from the binding total-emissions figure in accordance with the legal schedule and the relevant reporting year.
- Compare every staged row to canonical binding data. A non-match must become a classified discrepancy with source locator and reviewer disposition, not a silent fallback.
- Preserve unmatched, ambiguous and continuation rows in the report; no “best effort” merge may promote those values into production.
- Freeze a new immutable version; never mutate historical calculation-run snapshots.

## Promotion gate

The official dataset may be promoted only after:
1. Complete annex acquisition and hash verification.
2. Complete row-level reconciliation, including every staged legal row.
3. Zero unresolved high-risk discrepancies and explicit disposition for all unmatched/ambiguous rows.
4. Independent spot checks across sectors, countries, routes, dash/missing and corrected cases.
5. Golden calculation tests using the approved dataset, route and mark-up schedule.
6. Reviewer sign-off, immutable version identifier and rollback procedure.

## Status at current preflight

The legal pipeline contains 14,627 staged records. Seven curated canonical-source spot checks passed. 14,620 records remain pending canonical reconciliation. “Pending” means not reconciled; it does not prove the row is wrong or right. Nothing from this partial comparison is approved or promoted as the runtime legal dataset.

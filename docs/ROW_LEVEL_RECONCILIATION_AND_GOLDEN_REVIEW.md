# CBEOS row-level reconciliation and golden calculation review

**Result:** all 14,627 staged workbook rows match the corresponding extracted EUR-Lex table cells. The row-level machine comparison is complete; qualified source/legal review remains open. **No dataset was promoted.**

## Source integrity

- Acquired official-source archive SHA-256: `b5ac905c33c19bf5968e0e33ef97946ef0038d7256d1632e361c96e5f5661862`, verified locally.
- Corrective act source: Regulation (EU) 2026/1740, extracted HTML SHA-256 `754b3456caec30b8f6fae146805f9d7ddaeed2bdcf262e1d094043c4f8230d92`.
- Benchmark source: Regulation (EU) 2025/2620, extracted HTML SHA-256 `423a322e4def4b4bbcfd2a3c472e07417e32870dd76aed68008e4d7d42930cbf`.

## Row-level outcome

| Dataset | Staged | Extracted-source matches | Mismatches / ambiguous |
|---|---:|---:|---:|
| Annex I defaults | 12,540 | 12,540 | 0 |
| Annex IV precursor defaults | 283 | 283 | 0 |
| Benchmarks including continuation rows | 1,804 | 1,804 | 0 |
| **Total** | **14,627** | **14,627** | **0** |

Matching includes country, sector, normalized CN/TARIC code, production route and the numeric/default state. Direct, indirect and legally designated total fields are compared separately. Benchmark columns are checked independently by exact route; blank continuation cells are not converted to zero. The source extractor preserves table/row locators, but nested HTML tables can duplicate parent text and narrative provisions are not fully interpreted. Thus these results establish source-cell agreement, not completeness of legal interpretation.

## Golden calculations

All six independent cases pass. The most important case is Albania fertilisers: direct `2.730`, indirect `0.040`, legal total field `2.760`. The runtime uses `2.760 × 1.01 = 2.7876`; incorrectly summing the displayed components first would produce `2.7977`. Route-specific benchmark selection also passes: CN 7211 13 00, Column B, route (E) selects `0.072`; route mismatch is blocked. A blank benchmark route is blocked unless explicitly approved as route-independent.

Runtime arithmetic is isolated in `app.engine.calculate_marked_default_total` and tested for expected outputs, total-field semantics and invalid/non-finite values.

## Release gates still open

- Qualified review of annex/table completeness, country and code keys, units, effective dates, fallback semantics and production-route indicators against rendered legal text.
- Independent review of nested-table structure and source locators.
- Versioned canonical register approval and controlled promotion procedure.
- Production configuration/security review, off-host recovery drill, deployment verification and independent Antigravity review.

**Decision:** machine reconciliation and golden arithmetic checks pass. CBEOS is not cleared for live CBAM declarations, liability decisions or production dataset promotion.

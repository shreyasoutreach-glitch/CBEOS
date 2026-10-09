# Release Checklist (Do Not Mark Without Evidence)

## Regulatory and calculation
- [ ] Official source files retrieved, hashes recorded and effective-date relationships reviewed.
- [ ] All in-scope Annex I, Annex IV and benchmark rows reconciled or explicitly quarantined.
- [ ] Fallback and parent/group handling independently reviewed.
- [ ] Calculation formulas independently implemented and golden-tested.
- [ ] Actual-emissions/precursor workflows scoped and tested where supported.

## Product and data
- [ ] Evidence-to-result lineage demonstrated end-to-end.
- [ ] Human-review and correction workflows verified.
- [ ] Tenant isolation and role checks pass.
- [ ] Retention/deletion/export policies implemented and tested.

## Reliability and security
- [ ] Critical/high security findings resolved or release blocked.
- [ ] Backup restoration demonstrated.
- [ ] Migration and rollback tested.
- [ ] Logs/metrics/alerts tested and secrets not exposed.
- [ ] Dependency and secret scans reviewed.

## Release and independent verification
- [ ] Clean CI run passes on exact release commit.
- [ ] Known limitations and test denominators documented.
- [ ] Synthetic demo data labeled and contains no real customer data.
- [ ] Antigravity report attached to exact commit/package hashes.
- [ ] Findings triaged, fixes regression-tested and verification rerun.
- [ ] Production smoke tests and rollback path pass.
- [ ] Release owner approves go-live.

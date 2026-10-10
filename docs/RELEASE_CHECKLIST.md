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


## Live engineering status — 2026-10-11

### Verified in repository / CI evidence
- Public sandbox remote smoke test passed on the earlier deployed candidate: `/healthz`, `/readyz`, `/login`, and unauthenticated redirect.
- The source-governance report documents machine comparison of 14,627 staged rows to extracted EUR-Lex cells with zero reported mismatches. This is **not** legal approval; see `docs/ROW_LEVEL_RECONCILIATION_AND_GOLDEN_REVIEW.md`.
- `app/ops_readiness.py` now blocks production mode while required controls are open. It explicitly refuses to treat environment flags as a real PostgreSQL or object-storage implementation.
- The Render blueprint pins `CBAM_CUSTOMER_DATA_MODE=sandbox` and `/readyz` as its health-check path. Existing Render service settings still need confirmation in the dashboard.
- An admin-only `GET /api/integrations/probe` has been added. It performs bounded authenticated GET checks for configured model-provider and Resend endpoints, returns status codes only, and sends no email. This code-level capability is not evidence that the live credentials work.

### Still a hard NO-GO for customer production data
- A psycopg2 compatibility layer is now in the runtime module, and the dedicated Supabase project has the 35-table schema, RLS, tenant-integrity triggers and foreign-key indexes. However, Render still runs SQLite because the server-side PostgreSQL login/connection secret could not be installed through the available secret-entry action. The adapter has not been verified against the live database and the full regression suite has not been rerun on the exact current head.
- An S3-compatible object-storage adapter is implemented and unit-tested, but the deployed sandbox still uses local filesystem storage. Supabase Storage currently has zero buckets and zero storage policies. A private bucket, storage credentials, encryption/versioning configuration, canary upload/download/delete test, retention policy and recovery are not yet verified.
- No off-host restore drill, approved malware-scanning integration, shared rate limiter, independent security review, approved retention/data-processing controls, or regulatory promotion sign-off is evidenced.
- GitHub Actions CBEOS test run 38086359609 passed on commit `e7b42eaece33ef2e9b1edc04ce1c05a97a6c8257`. Render deployment of that commit was still in progress at last check; verify live smoke after it completes.
- Live integration probes must be run by an authorized administrator in the deployed environment. No outbound email is sent by the probe; actual delivery requires a separate controlled test and delivery webhook work.

### Required next acceptance criteria
1. Create a least-privilege server-only PostgreSQL login (do not use the `postgres` superuser in Render), install `CBAM_DATABASE_URL` through an approved secret-entry path, then exercise the adapter against the real Supabase schema, test every SQL dependency, seed data idempotently, and run the full regression suite against PostgreSQL; do not merely set `DATABASE_URL`.
2. Create a private Supabase Storage bucket through the Storage API/dashboard, create server-only S3 credentials, and verify bucket privacy, no anonymous read policies, encryption/versioning configuration, a synthetic upload/download/delete canary, approved retention and recovery. Keep the production gate blocked until that evidence exists.
3. Prove backup/restore and redeploy survival in a separate test environment.
4. Re-run full CI, remote smoke and authenticated synthetic end-to-end workflow at the exact head commit.
5. Run provider probes on Render with real credentials; then separately test a controlled model request and a single internal-recipient email with delivery confirmation.
6. Complete independent legal review of extracted tables, effective dates, fallback and route semantics, and obtain sign-off before promoting any canonical dataset.
7. Obtain independent security/privacy review and documented owner approval before changing the environment out of sandbox mode.


## Commercial direction — 2026-10-11

- Initial wedge: evidence recovery and review operations for Indian steel exporters with EU exposure, not a generic CBAM calculator or filing/certification claim. See `docs/COMMERCIAL_WEDGE.md`.
- Paid pilot price and duration are hypotheses only. Do not claim savings, willingness-to-pay, or regulatory correctness until a paid pilot and qualified review establish them.

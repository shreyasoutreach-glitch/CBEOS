# CBEOS Integration Matrix and Release Contract

Updated: 10 October 2026

This document distinguishes code-level integration from a live, credentialed connection. A green CI run does not mean external credentials have been installed or an external provider has been reached.

## Current integration status

| Integration | Current implementation | Live connection status | Safety boundary |
|---|---|---|---|
| Agent orchestration | Deterministic ordered workflow with persisted handoffs, specialist findings, summary and hash-chain verification | Works in local/synthetic tests | Agents recommend; they do not verify evidence, close exceptions, calculate authoritative liability, approve or submit declarations |
| OpenAI-compatible model endpoint | Optional `/chat/completions` commentary adapter using `urllib`; accepts a configurable base URL | **Not connected until deployment has a valid key + model and a live smoke test passes** | Commentary only; provider output cannot override deterministic state |
| Regulatory retrieval | Local curated index + manifest hash check + source-page excerpts | Local retrieval only when the approved index exists and hash matches | Hash integrity is not legal correctness; row-level legal reconciliation remains unverified |
| Supplier messaging | Supplier request states, due dates and suggested follow-up actions | **Not connected** | No emails/messages sent; no delivery claims |
| EU CBAM Registry | No filing/write integration | **Not connected** | No filing, submission or registry writes |
| Database | SQLite-backed local application database | Local/single-instance prototype | Do not assume persistent storage or multi-replica safety in an unconfigured Render service |
| Document extraction | Local PDF/XLSX/text extraction and candidate-fact creation | Local code path; format-specific extraction still needs broad evaluation | Extracted facts remain candidates until human review |
| Audit trail | Tenant-scoped audit events and hash-chain verification | Covered by regression tests; needs independent and deployment-environment review | Integrity evidence is not a legal approval |

## Model provider configuration

Supported environment variables:

- `CBAM_LLM_API_KEY`: secret token for an OpenAI-compatible API.
- `CBAM_LLM_MODEL`: exact model identifier supported by the provider.
- `CBAM_LLM_BASE_URL`: optional base URL, defaults to `https://api.openai.com/v1`. HTTPS is required for remote hosts; plain HTTP is permitted only for loopback development.

The server must never log or return the API key. A configured key/model is not proof of connectivity. Validate the exact model, permissions, rate limits, timeout behaviour, structured JSON response support and provider terms using synthetic data. The adapter degrades to deterministic rules if the provider fails. The integration-status endpoint reports configuration only, not successful live connectivity.

## Integration status endpoint

Authenticated, read-only endpoint: `GET /api/integrations`.

It reports:
- whether the model endpoint is configured (not whether a live request has succeeded),
- whether the local knowledge index and manifest hash agree,
- whether supplier messaging and CBAM Registry writes are connected,
- whether live client-data processing is enabled.

The endpoint must never include credentials. Keep it behind application authentication.

## Ordered workflow contract

1. Control Tower Orchestrator opens the run and establishes scope.
2. Intake & Scope inventories cases, lines, documents, installations and fact review states.
3. Evidence Quality evaluates missing requirements and provenance.
4. Supplier Operations prioritizes requests and overdue work; it does not send messages.
5. Reconciliation summarizes conflicts and open exceptions.
6. Regulatory Research retrieves source-grounded references and exposes uncertainty.
7. Calculation Integrity checks source authority, period, units and scenario-only calculations.
8. Commercial Exposure summarizes recorded exception impacts and scenario values with explicit caveats.
9. Verifier Readiness consolidates operational and calculation blockers.
10. Declaration Package QA checks existing package integrity and freshness; it does not generate, approve or submit.
11. Orchestrator returns prioritized actions and a traceable handoff to the human reviewer.

Every handoff is ordered and persisted. The chain is verifiable. Model critiques are advisory and must not alter the deterministic findings. Any workflow error must remain visible as a failed run and a safe next action.

## Render gate

Do not expose the application for customer-data processing until all of the following are complete:

- a production database/storage design is configured; the default local SQLite/upload filesystem must not be assumed durable on an ephemeral host,
- authentication, tenant isolation, upload limits, file storage, retention/deletion and backup/restore are reviewed in the actual deployment environment,
- exact-head CI passes,
- true multipart upload and user-visible export journeys are tested,
- a model provider is configured and live-tested if AI commentary is advertised,
- independent review is completed,
- the public site explicitly identifies sandbox/demo limitations and does not solicit confidential uploads.

A public, synthetic-data demo may be deployed separately once the exact candidate passes smoke tests. Do not describe it as production-ready.

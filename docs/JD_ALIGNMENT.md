# LSK Finance Reconciliation — Senior AI Platform Engineer JD alignment

## Implemented
- Tenant-scoped signed OIDC authorization and REST APIs.
- PostgreSQL finance records, per-source external-ID uniqueness, synchronous reference matching and stored exceptions.
- Terraform Cloud Run + Cloud SQL/Secrets/Registry and CI validation.
- Synthetic ERP/bank transaction schemas (no real data or payment transfers).

## Role match
- **Database engineering:** SQL schema, transactional deduplication and exact matching.
- **Payments-domain resilience:** mismatched records surface as exceptions, not silent settlement.
- **Security/IAM:** authenticated/tenant-scoped financial APIs; cloud runtime service identities.
- **Networking and operations:** Cloud Run/Cloud SQL connection configuration; production network policy, incident automation and disaster recovery absent.
- **Self-service developer experience:** API-driven, but developer infrastructure requests are handled by separate IDP repository.

## Production-style milestones
1. Add Pub/Sub ingestion, validated source adapters, durable retries/dead-letter handling and transactional outbox; test delivery at least once.
2. Add explicit exception ownership/approval workflow, reconciliation evidence and immutable accounting adjustments.
3. Support real-world financial cases: partial settlements, many-to-many matching, FX and chargebacks with synthetic data.
4. Use private Cloud SQL, least-privilege networking and threat modeling; run migrations and restore drills.
5. Build Prometheus/Cloud Monitoring SLO metrics, tracing, p95 latency and reproducible load/fault-injection tests.
6. Integrate read-only AI evidence review safely; require human approval for changes.

## Current limitation
The system requires explicit HTTP reconciliation calls and stores a simple latest result. It does not connect to a bank, pay any merchant, run queues, automatically resolve exceptions or implement a financial ledger.

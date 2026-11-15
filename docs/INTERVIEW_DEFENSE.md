# finance — interview defense

Portfolio project only, not a historical company production deployment.

1. Show local unit tests and a negative authorization test.
2. Explain how Cloud Run invoker IAM and signed OIDC scopes protect different trust boundaries.
3. Explain why SQL uniqueness/transactions matter for duplicate ingestion and exactly-one-pair reconciliation; describe missing cases such as partial settlement.
4. Explain Cloud Run vs GKE tradeoffs, Cloud SQL cost and HA limitations.
5. Explain why model access is NOT wired in this first implementation; introducing AI requires safe read-only tools, policy approval, audit logs, prompt injection defenses and evals.
6. Production gaps: migrations, HA, disaster recovery, private networking, SLO/alert policies, stress tests, tenant isolation and security assessment.

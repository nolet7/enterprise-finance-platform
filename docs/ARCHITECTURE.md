# GCP architecture

```mermaid
flowchart LR
  Caller[Approved caller] --> IAM[Cloud Run invoker IAM]
  IAM --> API[Cloud Run FastAPI]
  API --> JWT[OIDC and tenant validation]
  API --> SQL[(Cloud SQL PostgreSQL)]
  API --> Secret[Secret Manager]
  GitHub[GitHub OIDC CI] --> Registry[Artifact Registry]
  Registry --> API
```

Cloud Run IAM controls who can invoke the API; a separate signed JWT controls tenant and API scopes. The lab is intentionally limited and is NOT PCI compliant or production certified.

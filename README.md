# Finance Reconciliation & Exceptions API

Independent portfolio lab: fictional Chromalloy-inspired finance. Not evidence of an actual employer deployment.

GCP target: FastAPI, PostgreSQL, Cloud Run, Cloud SQL, Secret Manager, Artifact Registry, Terraform, GitHub Actions WIF.

## Security
OIDC-signed JWT, tenant and scope isolation, no payment processing, synthetic data. Restrict Cloud Run invoker IAM. Do not commit secrets.

## Cost
Create a billing budget first. Cloud SQL is charged while running. Budget alerts do not cap spending. No infrastructure is automatically deployed by this repository.

## Development
Run pip install -r requirements-dev.txt and DATABASE_URL=sqlite+pysqlite:///./test.db python -m pytest -q . See docs/ for design, operating risks, and interview guidance.

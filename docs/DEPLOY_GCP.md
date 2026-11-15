# GCP enterprise-style lab deployment guide

**Scope:** synthetic data only. No real identities, settlements, credit cards, or banking details. Terraform and Github workflows are authored, but **nothing is deployed automatically**.

## 0. Prerequisites and spending guardrails

- GCP billing account with available credits; an isolated GCP project per lab is preferable.
- gcloud CLI, Terraform >=1.6, Docker, and permission to administer required GCP services.
- Set a billing budget in Cloud Billing before creating resources. Budget alerts **do not stop spending**.
- Cloud SQL incurs hourly storage/instance costs even if Cloud Run scales to zero; destroy promptly.

Set variables in your own shell (choose actual values, no placeholders in apply):

~~~bash
export PROJECT_ID="YOUR_GCP_PROJECT_ID"
export REGION="us-central1"
export REPOSITORY="finance-lab"
export TF_STATE_BUCKET="YOUR_GLOBALLY_UNIQUE_TF_STATE_BUCKET"
gcloud config set project "$PROJECT_ID"
gcloud services enable storage.googleapis.com
~~~

## 1. Prepare encrypted remote Terraform state

~~~bash
gcloud storage buckets create "gs://$TF_STATE_BUCKET" --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://$TF_STATE_BUCKET" --versioning
~~~

Give only a dedicated Terraform deployer identity access to the bucket. State contains **sensitive values**, including database credentials. Review organizational restrictions and encryption requirements.

~~~bash
cd infra
terraform init -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="prefix=enterprise-finance-platform/lab"
~~~

## 2. Create Artifact Registry before the first application image

This lab is a two-step bootstrap because Cloud Run cannot deploy an image that does not yet exist. The one-off Terraform target is **only** for initially creating the registry; afterward use full plans:

~~~bash
export TF_VAR_db_password="REPLACE_WITH_RANDOM_SECRET_FROM_SECURE_SOURCE"
terraform plan -target=google_artifact_registry_repository.images -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
~~~

Do **not** commit bootstrap.tfplan; Terraform plan/state files may contain sensitive values. Set all other Terraform variables in a private tfvars file or environment.

## 3. Set up GitHub Actions Workload Identity Federation

Create a dedicated deployer service account with narrowly scoped Artifact Registry writer rights. Configure a GCP Workload Identity Pool/provider restricted to **the exact GitHub repository and ref or GitHub Environment**. Grant roles/iam.workloadIdentityUser on the deployer service account to that principal set. Avoid JSON credential keys.

Configure the protected GitHub environment `gcp-lab` and repository/environment variables:

- `GCP_PROJECT_ID` — your project ID
- `GCP_REGION` — registry region
- `GCP_ARTIFACT_REPOSITORY` — Artifact Registry repository ID
- `GCP_WORKLOAD_IDENTITY_PROVIDER` — full provider resource name
- `GCP_DEPLOYER_SERVICE_ACCOUNT` — deployer service account email

Run `Publish OCI Image` manually from the GitHub Actions UI. After it succeeds, obtain the pushed container **digest**, not a mutable tag, and update Terraform `image`.

See Google documentation for detailed WIF setup:
https://github.com/google-github-actions/auth

## 4. Deploy the API

Set `project_id`, `region`, `image`, OIDC issuer/audience/JWKS URL and, for access project, Gemini model ID. Provision a real identity provider whose access JWT includes `tenant_id` and least-privilege `scope` claims.

~~~bash
terraform plan -out=deploy.tfplan
terraform apply deploy.tfplan
terraform output service_uri
~~~

No `allUsers` invoker binding is created. Explicitly grant `roles/run.invoker` only to designated principals (users or upstream gateway service accounts). This is **separate** from app-level JWT validation.

## 5. Initialize the database schema

The API does not migrate the database on startup. For initial lab bootstrap, create a **one-off Cloud Run Job** using the published image, same runtime service account, Cloud SQL connection and DB secret, then execute `python scripts/migrate.py`. Never run destructive schema changes per web request. Switch to versioned Alembic migrations with canary/backward-compatible rollouts before production.

## 6. Validate

- CI must show successful unit tests, lint, dependency audit and Terraform validation.
- Verify /healthz and /readyz **through Cloud Run IAM authenticated invocation**.
- Issue an OIDC JWT for a test tenant; test valid permissions, missing scope, expired token, tenant isolation and duplicate requests.
- Measure 4xx/5xx error rates, DB connection pool usage and p95 latency. Add Cloud Monitoring alert policies before calling this production-grade.
- Run load tests on synthetic data. Verify backups and execute a restore drill.

## 7. Cleanup

Terraform uses deletion protection by default. Confirm resources are disposable, set `deletion_protection=false`, plan and apply the change, then destroy the lab. Verify Cloud SQL, Cloud Run, Artifact Registry, Secret Manager versions and remaining storage are deleted. Terraform remote state bucket may persist separately.

## Production gaps

Private-IP-only Cloud SQL/VPC, HA/DR, database migrations, richer audit logging and data retention, tracing/SLO dashboards and alert policies, hardened rate limiting and bot protections, API gateway configuration, compliance review, security testing, and a controlled release strategy. These are **explicit future work**, not completed production certification.

## Current schema migration procedure supersedes old bootstrap notes

Earlier references to `Base.metadata.create_all()` are obsolete. The one-off job now runs the reviewed Alembic `0001_initial` revision through `python scripts/migrate.py`; see [Schema Migration Guide](SCHEMA_MIGRATION.md). **Existing database tables must be schema-compared and baselined before applying the migration.** The new GitHub CI job tests the migration using a temporary PostgreSQL 16 service; this does not validate high availability, production traffic or backup restore.

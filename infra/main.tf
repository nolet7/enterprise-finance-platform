locals {
  name = "finance-${var.environment}"
}
resource "google_project_service" "apis" {
  for_each = toset(["run.googleapis.com","sqladmin.googleapis.com","secretmanager.googleapis.com","artifactregistry.googleapis.com","iam.googleapis.com","compute.googleapis.com","servicenetworking.googleapis.com"])
  project  = var.project_id
  service  = each.key
  disable_on_destroy = false
}
resource "google_service_account" "runtime" {
  account_id   = "finance-${var.environment}-runtime"
  display_name = "finance runtime"
}
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "finance-${var.environment}"
  format        = "DOCKER"
  depends_on = [google_project_service.apis]
}
resource "google_sql_database_instance" "database" {
  name                = "finance-${var.environment}-db"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.deletion_protection
  lifecycle {
    precondition {
      condition = var.environment != "prod" || (
        var.enable_private_sql &&
        var.db_availability_type == "REGIONAL" &&
        var.db_tier != "db-f1-micro"
      )
      error_message = "LSK production deployment requires private Cloud SQL, regional HA, and a dedicated non-micro database tier."
    }
  }
  settings {
    tier = var.db_tier
    availability_type = var.db_availability_type
    backup_configuration {
      enabled = true
    }
    ip_configuration {
      ipv4_enabled = !var.enable_private_sql
      private_network = var.enable_private_sql ? google_compute_network.private[0].id : null
    }
  }
  depends_on = [google_project_service.apis, google_service_networking_connection.private_services]
}
resource "google_sql_database" "platform" {
  name     = "platform"
  instance = google_sql_database_instance.database.name
}
resource "google_sql_user" "app" {
  name     = "app"
  instance = google_sql_database_instance.database.name
  password = var.db_password
}
resource "google_secret_manager_secret" "database_url" {
  secret_id = "finance-${var.environment}-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
resource "google_secret_manager_secret_version" "db_version" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+psycopg://app:${urlencode(var.db_password)}@/platform?host=/cloudsql/${google_sql_database_instance.database.connection_name}"
}
resource "google_secret_manager_secret_iam_member" "runtime" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_cloud_run_v2_service" "api" {
  name                = local.name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.deletion_protection
  template {
    service_account = google_service_account.runtime.email
    dynamic "vpc_access" {
      for_each = var.enable_private_sql ? [1] : []
      content {
        network_interfaces {
          network    = google_compute_network.private[0].name
          subnetwork = google_compute_subnetwork.private[0].name
          tags       = ["lsk-${var.environment}-api"]
        }
        egress = "PRIVATE_RANGES_ONLY"
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.database.connection_name]
      }
    }
    containers {
      image = var.image
      ports {
        container_port = 8080
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "LSK_ENFORCE_RESIDENCY"
        value = "true"
      }
      env {
        name  = "LSK_DEPLOYMENT_REGION"
        value = var.region
      }
      env {
        name  = "LSK_TENANT_REGION_POLICY"
        value = jsonencode(var.tenant_region_policy)
      }

      env {
        name = "OIDC_ISSUER"
        value = var.oidc_issuer
      }
      env {
        name = "OIDC_AUDIENCE"
        value = var.oidc_audience
      }
      env {
        name = "OIDC_JWKS_URL"
        value = var.oidc_jwks_url
      }
    }
  }
  depends_on = [google_project_service.apis,google_project_iam_member.sql_client,google_secret_manager_secret_iam_member.runtime]
}
# Intentionally no allUsers invoker IAM binding; grant to known trusted principals only.
output "service_uri" {
  value = google_cloud_run_v2_service.api.uri
}
output "artifact_registry" {
  value = google_artifact_registry_repository.images.name
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}
output "sql_connection_name" {
  value = google_sql_database_instance.database.connection_name
}
output "database_secret_id" {
  value = google_secret_manager_secret.database_url.secret_id
}

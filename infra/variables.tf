variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "environment" {
  type    = string
  default = "lab"
}
variable "image" {
  type        = string
  description = "Artifact Registry image by immutable sha256 digest"
}
variable "db_password" {
  type      = string
  sensitive = true
}
variable "oidc_issuer" {
  type = string
}
variable "oidc_audience" {
  type = string
}
variable "oidc_jwks_url" {
  type = string
}
variable "deletion_protection" {
  type    = bool
  default = true
}

variable "tenant_region_policy" {
  type        = map(list(string))
  description = "Signed JWT tenant_id -> allowed deployment regions. Empty map denies every tenant."
  default     = {}
}
variable "db_tier" {
  type        = string
  description = "Cloud SQL instance tier: choose an HA-capable size for production."
  default     = "db-f1-micro"
}
variable "db_availability_type" {
  type    = string
  default = "ZONAL"
  validation {
    condition     = contains(["ZONAL", "REGIONAL"], var.db_availability_type)
    error_message = "Use ZONAL or REGIONAL."
  }
}

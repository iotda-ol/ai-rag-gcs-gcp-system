# Common resource labels applied to every GCS bucket and Secret Manager secret.
# Merge with resource-specific labels using: merge(local.common_labels, { component = "..." })

locals {
  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    app         = var.app_name
  }
}

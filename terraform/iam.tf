# ── RAG service account ─────────────────────────────────────────────────────
resource "google_service_account" "rag_sa" {
  account_id   = "${var.app_name}-pipeline-sa"
  display_name = "RAG Pipeline Service Account"
  description  = var.rag_sa_description
  project      = var.project_id

  depends_on = [google_project_service.apis]
}

# ── Project-level IAM roles for the RAG service account ─────────────────────
# Only roles that cannot be scoped to individual resources are listed here.
# - GCS access  → granted per-bucket in gcs.tf (roles/storage.objectAdmin)
# - Secret access → granted per-secret in secret_manager.tf (roles/secretmanager.secretAccessor)
locals {
  rag_sa_project_roles = [
    "roles/aiplatform.user", # Vertex AI APIs – no resource-level binding available
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
  ]
}

resource "google_project_iam_member" "rag_sa_roles" {
  for_each = toset(local.rag_sa_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.rag_sa.email}"
}

# ── Allow Vertex AI service agent to impersonate the RAG SA ─────────────────
resource "google_service_account_iam_member" "vertex_ai_impersonate_rag_sa" {
  service_account_id = google_service_account.rag_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-aiplatform.iam.gserviceaccount.com"
}

data "google_project" "project" {
  project_id = var.project_id
  depends_on = [google_project_service.apis]
}

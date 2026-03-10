# Enable all GCP APIs required by the RAG system.
# Every resource module depends on this file so APIs are ready before resources are created.

locals {
  required_apis = toset([
    "aiplatform.googleapis.com",    # Vertex AI (RAG Engine, embeddings, Gemini)
    "storage.googleapis.com",       # Cloud Storage
    "secretmanager.googleapis.com", # Secret Manager
    "iam.googleapis.com",           # IAM
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com", # needed by Vertex AI networking
    "servicenetworking.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com", # Cloud Run (optional serving layer)
  ])
}

resource "google_project_service" "apis" {
  for_each = local.required_apis

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

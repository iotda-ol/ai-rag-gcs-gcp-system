# All application configuration is stored in Secret Manager so the deployed
# application only needs the project_id at runtime (similar to aws_profile).
#
# Naming convention: <app_name>-<key>  (e.g. rag-project-id, rag-region)

locals {
  # Map of secret ID → initial secret value (plaintext).
  # Sensitive values (API keys, credentials) are placeholders; operators should
  # update them via `gcloud secrets versions add` or the GCP console.
  app_secrets = {
    "project-id"                    = var.project_id
    "region"                        = var.region
    "environment"                   = var.environment
    "raw-docs-bucket"               = local.raw_bucket_name
    "processed-docs-bucket"         = local.processed_bucket_name
    "rag-corpus-display-name"       = var.rag_corpus_display_name
    "embedding-model"               = var.embedding_model
    "generation-model"              = var.generation_model
    "rag-chunk-size"                = tostring(var.rag_chunk_size)
    "rag-chunk-overlap"             = tostring(var.rag_chunk_overlap)
    "rag-retrieval-top-k"           = tostring(var.rag_retrieval_top_k)
    "rag-vector-distance-threshold" = tostring(var.rag_vector_distance_threshold)
    "rag-sa-email"                  = google_service_account.rag_sa.email
    # Operator-managed secrets (initial value is a safe placeholder)
    "gemini-api-key"                = "REPLACE_WITH_ACTUAL_KEY"
    "vertex-ai-endpoint-override"   = ""
    "langchain-api-key"             = "REPLACE_WITH_ACTUAL_KEY"
  }
}

resource "google_secret_manager_secret" "app_secrets" {
  for_each = local.app_secrets

  secret_id = "${var.app_name}-${each.key}"
  project   = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    component   = "rag-config"
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "app_secrets" {
  for_each = local.app_secrets

  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value

  lifecycle {
    # Prevent Terraform from overwriting operator-managed secret versions.
    ignore_changes = [secret_data]
  }
}

# ── Grant the RAG service account access to all managed secrets ──────────────
resource "google_secret_manager_secret_iam_member" "rag_sa_access" {
  for_each = local.app_secrets

  secret_id = google_secret_manager_secret.app_secrets[each.key].secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

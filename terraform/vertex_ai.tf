# Vertex AI RAG Engine resources
# Uses the google-beta provider because RAG Engine is still in preview.
#
# NOTE: `google_vertex_ai_rag_corpus` was introduced in google-beta ~5.14 and
# may not be present in all 5.x patch releases.  If `terraform validate` reports
# "unsupported resource type", pin the google-beta provider to a version that
# includes the resource or upgrade to 6.x once GA support is available.

# ── RAG Corpus ───────────────────────────────────────────────────────────────
resource "google_vertex_ai_rag_corpus" "corpus" {
  provider     = google-beta
  project      = var.project_id
  location     = var.region
  display_name = "${var.app_name}-${var.rag_corpus_display_name}-${var.environment}"
  description  = "Vertex AI RAG corpus for the ${var.app_name} system (${var.environment})"

  rag_embedding_model_config {
    vertex_prediction_endpoint {
      endpoint = "projects/${var.project_id}/locations/${var.region}/publishers/google/models/${var.embedding_model}"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_service_account.rag_sa,
  ]
}

# ── Store the corpus resource name in Secret Manager ─────────────────────────
resource "google_secret_manager_secret" "rag_corpus_name" {
  secret_id = "${var.app_name}-rag-corpus-name"
  project   = var.project_id

  labels = merge(local.common_labels, { component = "rag-vertex-ai" })

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "rag_corpus_name" {
  secret      = google_secret_manager_secret.rag_corpus_name.id
  secret_data = google_vertex_ai_rag_corpus.corpus.name
}

resource "google_secret_manager_secret_iam_member" "rag_sa_corpus_name_access" {
  secret_id = google_secret_manager_secret.rag_corpus_name.secret_id
  project   = var.project_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_sa.email}"
}

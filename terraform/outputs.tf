output "project_id" {
  description = "GCP project ID."
  value       = var.project_id
}

output "region" {
  description = "GCP region."
  value       = var.region
}

output "rag_sa_email" {
  description = "Email of the RAG pipeline service account."
  value       = google_service_account.rag_sa.email
}

output "raw_docs_bucket" {
  description = "Name of the raw-documents GCS bucket."
  value       = google_storage_bucket.raw_docs.name
}

output "processed_docs_bucket" {
  description = "Name of the processed-documents GCS bucket."
  value       = google_storage_bucket.processed_docs.name
}

output "rag_corpus_name" {
  description = "Full resource name of the Vertex AI RAG corpus."
  value       = google_vertex_ai_rag_corpus.corpus.name
}

output "rag_corpus_id" {
  description = "Numeric ID of the Vertex AI RAG corpus."
  value       = google_vertex_ai_rag_corpus.corpus.id
}

output "secret_prefix" {
  description = "Prefix used for all Secret Manager secret IDs (e.g. 'rag-project-id')."
  value       = "${var.app_name}-"
}

output "secret_ids" {
  description = "Map of logical secret key → Secret Manager secret ID."
  sensitive   = true
  value = {
    for k, s in google_secret_manager_secret.app_secrets :
    k => s.secret_id
  }
}

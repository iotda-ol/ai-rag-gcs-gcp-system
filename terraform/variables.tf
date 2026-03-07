variable "project_id" {
  description = "GCP project ID (the only required input – analogous to aws_profile)."
  type        = string
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone within the region."
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)."
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Short name used as a prefix for all created resources."
  type        = string
  default     = "rag"
}

# ---------- GCS ----------

variable "raw_docs_bucket_suffix" {
  description = "Suffix appended to the project-ID to form the raw-documents bucket name."
  type        = string
  default     = "raw-docs"
}

variable "processed_docs_bucket_suffix" {
  description = "Suffix appended to the project-ID to form the processed-documents bucket name."
  type        = string
  default     = "processed-docs"
}

variable "bucket_location" {
  description = "GCS bucket location (multi-region or region)."
  type        = string
  default     = "US"
}

variable "bucket_storage_class" {
  description = "Default storage class for GCS buckets."
  type        = string
  default     = "STANDARD"
}

variable "bucket_versioning_enabled" {
  description = "Enable object versioning on GCS buckets."
  type        = bool
  default     = true
}

# ---------- Vertex AI ----------

variable "embedding_model" {
  description = "Vertex AI text-embedding model used for RAG indexing."
  type        = string
  default     = "text-embedding-005"
}

variable "rag_corpus_display_name" {
  description = "Display name of the Vertex AI RAG corpus."
  type        = string
  default     = "rag-corpus"
}

variable "rag_chunk_size" {
  description = "Chunk size (tokens) for RAG document splitting."
  type        = number
  default     = 512
}

variable "rag_chunk_overlap" {
  description = "Overlap (tokens) between adjacent RAG chunks."
  type        = number
  default     = 100
}

variable "generation_model" {
  description = "Vertex AI generative model used for RAG answer synthesis."
  type        = string
  default     = "gemini-1.5-flash-002"
}

variable "rag_retrieval_top_k" {
  description = "Number of context chunks retrieved per query."
  type        = number
  default     = 10
}

variable "rag_vector_distance_threshold" {
  description = "Maximum vector distance for retrieved chunks."
  type        = number
  default     = 0.5
}

# ---------- Secret Manager ----------

variable "secret_replication_policy" {
  description = "Replication policy for Secret Manager secrets (automatic | managed)."
  type        = string
  default     = "automatic"

  validation {
    condition     = contains(["automatic", "managed"], var.secret_replication_policy)
    error_message = "secret_replication_policy must be 'automatic' or 'managed'."
  }
}

# ---------- IAM ----------

variable "rag_sa_description" {
  description = "Description for the RAG service account."
  type        = string
  default     = "Service account used by the Vertex AI RAG pipeline"
}

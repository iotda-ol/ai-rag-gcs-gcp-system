variable "project_id" {
  description = "GCP project ID (the only required input – analogous to aws_profile)."
  type        = string

  validation {
    condition     = length(var.project_id) > 0
    error_message = "project_id must not be empty."
  }
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "us-central1"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.region))
    error_message = "region must be a valid GCP region (e.g. us-central1, europe-west1)."
  }
}

variable "zone" {
  description = "GCP zone within the region."
  type        = string
  default     = "us-central1-a"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+-[a-z]$", var.zone))
    error_message = "zone must be a valid GCP zone (e.g. us-central1-a)."
  }
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "app_name" {
  description = "Short name used as a prefix for all created resources."
  type        = string
  default     = "rag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,18}[a-z0-9]$", var.app_name))
    error_message = "app_name must be 2-20 lowercase letters, digits, or hyphens, and must start with a letter."
  }
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

  validation {
    condition     = contains(["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"], var.bucket_storage_class)
    error_message = "bucket_storage_class must be one of: STANDARD, NEARLINE, COLDLINE, ARCHIVE."
  }
}

variable "bucket_versioning_enabled" {
  description = "Enable object versioning on GCS buckets."
  type        = bool
  default     = true
}

variable "force_destroy_buckets" {
  description = "Allow Terraform to destroy non-empty GCS buckets. Set to false in production."
  type        = bool
  default     = false
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

  validation {
    condition     = var.rag_chunk_size >= 64 && var.rag_chunk_size <= 2048
    error_message = "rag_chunk_size must be between 64 and 2048 tokens."
  }
}

variable "rag_chunk_overlap" {
  description = "Overlap (tokens) between adjacent RAG chunks."
  type        = number
  default     = 100

  validation {
    condition     = var.rag_chunk_overlap >= 0 && var.rag_chunk_overlap <= 1024
    error_message = "rag_chunk_overlap must be between 0 and 1024 tokens."
  }
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

  validation {
    condition     = var.rag_retrieval_top_k >= 1 && var.rag_retrieval_top_k <= 100
    error_message = "rag_retrieval_top_k must be between 1 and 100."
  }
}

variable "rag_vector_distance_threshold" {
  description = "Maximum vector distance for retrieved chunks."
  type        = number
  default     = 0.5

  validation {
    condition     = var.rag_vector_distance_threshold > 0 && var.rag_vector_distance_threshold <= 1
    error_message = "rag_vector_distance_threshold must be between 0 (exclusive) and 1 (inclusive)."
  }
}

# ---------- IAM ----------

variable "rag_sa_description" {
  description = "Description for the RAG service account."
  type        = string
  default     = "Service account used by the Vertex AI RAG pipeline"
}

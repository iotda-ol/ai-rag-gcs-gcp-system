locals {
  raw_bucket_name       = "${var.project_id}-${var.app_name}-${var.raw_docs_bucket_suffix}"
  processed_bucket_name = "${var.project_id}-${var.app_name}-${var.processed_docs_bucket_suffix}"
}

# ── Raw documents bucket ────────────────────────────────────────────────────
resource "google_storage_bucket" "raw_docs" {
  name          = local.raw_bucket_name
  project       = var.project_id
  location      = var.bucket_location
  storage_class = var.bucket_storage_class

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = var.bucket_versioning_enabled
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 90
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                   = 365
      with_state            = "ARCHIVED"
      num_newer_versions    = 3
    }
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    component   = "rag-raw-docs"
  }

  depends_on = [google_project_service.apis]
}

# ── Processed / chunked documents bucket ───────────────────────────────────
resource "google_storage_bucket" "processed_docs" {
  name          = local.processed_bucket_name
  project       = var.project_id
  location      = var.bucket_location
  storage_class = var.bucket_storage_class

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = var.bucket_versioning_enabled
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 180
    }
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    component   = "rag-processed-docs"
  }

  depends_on = [google_project_service.apis]
}

# ── IAM: grant RAG service account access to both buckets ──────────────────
resource "google_storage_bucket_iam_member" "rag_sa_raw_docs_admin" {
  bucket = google_storage_bucket.raw_docs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

resource "google_storage_bucket_iam_member" "rag_sa_processed_docs_admin" {
  bucket = google_storage_bucket.processed_docs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_sa.email}"
}

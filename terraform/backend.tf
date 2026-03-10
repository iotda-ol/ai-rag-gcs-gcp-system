# Remote state backend — Google Cloud Storage
#
# IMPORTANT: Create the state bucket BEFORE running `terraform init`:
#
#   gcloud storage buckets create gs://<PROJECT_ID>-terraform-state \
#     --location=us-central1 \
#     --uniform-bucket-level-access \
#     --public-access-prevention
#
# Then initialise Terraform, providing your project's state bucket:
#
#   terraform init \
#     -backend-config="bucket=<PROJECT_ID>-terraform-state"
#
# Workspaces map to state file prefixes, so running:
#   terraform workspace new staging
# will store state under  rag-system/staging/default.tfstate

terraform {
  backend "gcs" {
    # Supply the bucket name at init time — never hard-code a project-specific value here:
    #   terraform init -backend-config="bucket=<PROJECT_ID>-terraform-state"
    prefix = "rag-system"
  }
}

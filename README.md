# ai-rag-gcs-gcp-system

GCP Vertex AI RAG system with GCS storage, Google Secret Manager for all configuration, and Terraform for one-command deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  User / Application                                             │
│                                                                 │
│  python -m src.main --project-id <PROJECT_ID> query "..."      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ project_id only
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Google Secret Manager  (all config live here)                  │
│  rag-region • rag-embedding-model • rag-generation-model        │
│  rag-raw-docs-bucket • rag-processed-docs-bucket                │
│  rag-rag-corpus-name • rag-rag-chunk-size • …                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌───────────────┐ ┌──────────┐ ┌─────────────────┐
    │  GCS Buckets  │ │ Vertex AI│ │  Gemini 1.5     │
    │  raw-docs     │ │ RAG      │ │  Flash / Pro    │
    │  processed-   │ │ Engine   │ │  (generation)   │
    │  docs         │ │(indexing)│ │                 │
    └───────────────┘ └──────────┘ └─────────────────┘
```

**Key design principle:** The GCP project ID is the only value required at runtime — exactly like `aws_profile` in AWS.  Every other setting (bucket names, model IDs, chunk sizes, API keys) is stored in **Google Secret Manager** and fetched automatically.

---

## Repository Layout

```
.
├── terraform/                  # Infrastructure-as-Code (Terraform)
│   ├── versions.tf             # Provider requirements (google ~> 5.0)
│   ├── variables.tf            # project_id (required) + all defaulted vars
│   ├── apis.tf                 # Enable all required GCP APIs
│   ├── gcs.tf                  # GCS buckets (raw-docs, processed-docs)
│   ├── iam.tf                  # Service account + project IAM roles
│   ├── secret_manager.tf       # All config/secrets in Secret Manager
│   ├── vertex_ai.tf            # Vertex AI RAG corpus
│   └── outputs.tf              # Useful post-deploy outputs
├── src/
│   ├── config/
│   │   └── settings.py         # Typed settings loaded from Secret Manager
│   ├── utils/
│   │   ├── secrets.py          # Secret Manager client wrapper
│   │   └── gcs.py              # GCS upload/download helpers
│   ├── rag/
│   │   ├── corpus.py           # RAG corpus lifecycle management
│   │   ├── ingestor.py         # Document ingestion (GCS + RAG import)
│   │   ├── retriever.py        # Retrieval + Gemini generation
│   │   └── pipeline.py         # End-to-end facade
│   └── main.py                 # CLI entrypoint
├── tests/
│   ├── test_utils.py           # Unit tests for secrets & GCS helpers
│   └── test_rag.py             # Unit tests for RAG components
├── requirements.txt
├── setup.py
└── .gitignore
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Terraform | ≥ 1.5 |
| Python | ≥ 3.11 |
| gcloud CLI | latest |
| A GCP Project with billing enabled | – |

---

## Quickstart

### 1 — Deploy infrastructure

```bash
cd terraform

# Authenticate
gcloud auth application-default login

# Initialise Terraform
terraform init

# Preview the plan — project_id is the ONLY required variable
terraform plan -var="project_id=YOUR_PROJECT_ID"

# Apply
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

Terraform will:
- Enable all required GCP APIs
- Create two GCS buckets (`<project>-rag-raw-docs`, `<project>-rag-processed-docs`)
- Create a dedicated service account with least-privilege IAM roles
- Create a Vertex AI RAG corpus using `text-embedding-005`
- Store **every** configuration value in Google Secret Manager under the prefix `rag-*`

Optional variables (all have sensible defaults):

```bash
terraform apply \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=europe-west1" \
  -var="environment=prod" \
  -var="generation_model=gemini-1.5-pro-002" \
  -var="rag_retrieval_top_k=15"
```

### 2 — Install the Python package

```bash
pip install -e ".[dev]"
```

### 3 — Ingest documents

```bash
# Upload a single PDF and import it into the RAG corpus
python -m src.main --project-id YOUR_PROJECT_ID ingest --file docs/report.pdf

# Upload an entire directory
python -m src.main --project-id YOUR_PROJECT_ID ingest --dir ./documents

# Import files already in GCS
python -m src.main --project-id YOUR_PROJECT_ID ingest --gcs-prefix gs://my-bucket/docs/
```

### 4 — Query

```bash
# Generate a grounded answer with Gemini
python -m src.main --project-id YOUR_PROJECT_ID query "What is the annual revenue?"

# Retrieve context chunks only (no generation)
python -m src.main --project-id YOUR_PROJECT_ID query "What is the annual revenue?" --retrieve-only

# List all indexed files
python -m src.main --project-id YOUR_PROJECT_ID list-files
```

Set `GCP_PROJECT_ID` once to avoid repeating `--project-id`:

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
python -m src.main query "Summarise the Q3 earnings."
```

---

## Using the Python API

```python
from src.rag.pipeline import RAGPipeline

# project_id is the only required parameter
pipeline = RAGPipeline.from_project("YOUR_PROJECT_ID")

# Ingest
pipeline.ingest_directory("/path/to/docs")

# Query
response = pipeline.query("What are the key findings?")
print(response.answer)

for chunk in response.retrieved_chunks:
    print(f"  [{chunk.score:.2f}] {chunk.source_uri}")
```

---

## Configuration via Secret Manager

All settings are stored as Secret Manager secrets with prefix `rag-`:

| Secret ID | Description | Default |
|-----------|-------------|---------|
| `rag-project-id` | GCP project ID | *(required)* |
| `rag-region` | GCP region | `us-central1` |
| `rag-environment` | Deployment environment | `dev` |
| `rag-raw-docs-bucket` | Raw documents GCS bucket | `<project>-rag-raw-docs` |
| `rag-processed-docs-bucket` | Processed docs GCS bucket | `<project>-rag-processed-docs` |
| `rag-rag-corpus-name` | Vertex AI RAG corpus resource name | *(set by Terraform)* |
| `rag-embedding-model` | Vertex AI embedding model | `text-embedding-005` |
| `rag-generation-model` | Gemini generative model | `gemini-1.5-flash-002` |
| `rag-rag-chunk-size` | Chunk size (tokens) | `512` |
| `rag-rag-chunk-overlap` | Overlap between chunks (tokens) | `100` |
| `rag-rag-retrieval-top-k` | Number of retrieved chunks per query | `10` |
| `rag-rag-vector-distance-threshold` | Max vector distance for retrieval | `0.5` |
| `rag-gemini-api-key` | Gemini API key (operator-managed) | *(placeholder)* |
| `rag-langchain-api-key` | LangChain API key (operator-managed) | *(placeholder)* |

Update operator-managed secrets:

```bash
echo -n "YOUR_KEY" | gcloud secrets versions add rag-gemini-api-key --data-file=-
```

---

## Running Tests

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

All tests use mocks for GCP services — no live project required.

---

## Tear Down

```bash
cd terraform
terraform destroy -var="project_id=YOUR_PROJECT_ID"
```

---

## Security Notes

- All secrets and config are stored in **Google Secret Manager** — nothing in environment variables or code.
- GCS buckets enforce **uniform bucket-level access** and **public access prevention**.
- The RAG service account follows the **principle of least privilege**.
- Service account keys are **never created** — authentication uses Application Default Credentials (ADC) / Workload Identity.
- `.gitignore` prevents accidental commit of `*.tfvars`, `*.json` credentials, and `.env` files.

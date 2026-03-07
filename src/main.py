"""CLI entrypoint for the Vertex AI RAG system.

Usage examples::

    # Ingest a local directory of documents
    python -m src.main --project-id my-gcp-project ingest --dir /path/to/docs

    # Query the RAG system
    python -m src.main --project-id my-gcp-project query "What is the return policy?"

    # List corpus files
    python -m src.main --project-id my-gcp-project list-files

Environment variable alternative (avoids repeating --project-id)::

    export GCP_PROJECT_ID=my-gcp-project
    python -m src.main ingest --dir /path/to/docs
    python -m src.main query "What is the return policy?"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag",
        description="GCP Vertex AI RAG system with GCS and Secret Manager",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="GCP project ID (default: $GCP_PROJECT_ID).",
    )
    parser.add_argument(
        "--no-secret-manager",
        action="store_true",
        default=False,
        help="Load config from environment variables instead of Secret Manager.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── ingest ────────────────────────────────────────────────────────
    ingest = sub.add_parser("ingest", help="Ingest documents into the RAG corpus.")
    ingest_group = ingest.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument("--file", help="Path to a single document.")
    ingest_group.add_argument("--dir", help="Path to a directory of documents.")
    ingest_group.add_argument("--gcs-prefix", help="GCS prefix to import (gs://bucket/path or path).")
    ingest.add_argument(
        "--gcs-prefix-dest",
        default="uploads",
        help="Destination GCS prefix when uploading local files (default: uploads).",
    )

    # ── query ─────────────────────────────────────────────────────────
    query = sub.add_parser("query", help="Query the RAG system.")
    query.add_argument("question", help="Natural-language question.")
    query.add_argument(
        "--retrieve-only",
        action="store_true",
        help="Return retrieved chunks without generation.",
    )
    query.add_argument("--system-instruction", default=None, help="System prompt for the generative model.")

    # ── list-files ────────────────────────────────────────────────────
    sub.add_parser("list-files", help="List files in the RAG corpus.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    project_id = args.project_id
    if not project_id:
        parser.error(
            "GCP project ID is required.  Pass --project-id or set $GCP_PROJECT_ID."
        )

    # Lazy import to keep startup fast
    from src.rag.pipeline import RAGPipeline

    use_sm = not args.no_secret_manager
    logger.info("Initialising RAG pipeline (project=%s, secret_manager=%s)", project_id, use_sm)
    pipeline = RAGPipeline.from_project(project_id=project_id, use_secret_manager=use_sm)

    # ── ingest ────────────────────────────────────────────────────────
    if args.command == "ingest":
        if args.file:
            pipeline.ingest_file(args.file, gcs_prefix=args.gcs_prefix_dest)
            print(f"Ingested file: {args.file}")
        elif args.dir:
            pipeline.ingest_directory(args.dir, gcs_prefix=args.gcs_prefix_dest)
            print(f"Ingested directory: {args.dir}")
        elif args.gcs_prefix:
            pipeline.ingest_gcs_prefix(args.gcs_prefix)
            print(f"Ingested GCS prefix: {args.gcs_prefix}")

    # ── query ─────────────────────────────────────────────────────────
    elif args.command == "query":
        if args.retrieve_only:
            chunks = pipeline.retrieve(args.question)
            for i, chunk in enumerate(chunks, 1):
                print(f"\n[{i}] score={chunk.score:.4f}  source={chunk.source_uri}")
                print(chunk.text[:500])
        else:
            response = pipeline.query(
                args.question,
                system_instruction=args.system_instruction,
            )
            print("\n" + "=" * 60)
            print(f"ANSWER (model: {response.model})")
            print("=" * 60)
            print(response.answer)
            if response.retrieved_chunks:
                print("\nSOURCES:")
                seen = set()
                for chunk in response.retrieved_chunks:
                    if chunk.source_uri not in seen:
                        print(f"  • {chunk.source_uri}")
                        seen.add(chunk.source_uri)

    # ── list-files ────────────────────────────────────────────────────
    elif args.command == "list-files":
        corpus = pipeline.corpus
        from src.rag.corpus import CorpusManager
        files = CorpusManager(pipeline.settings).list_corpus_files(corpus.name)
        if not files:
            print("No files in the RAG corpus.")
        else:
            print(f"Files in corpus '{corpus.display_name}':")
            for f in files:
                print(f"  {f.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

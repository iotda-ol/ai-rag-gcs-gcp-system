"""RAG retrieval: query the Vertex AI RAG corpus and optionally generate an answer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import vertexai
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool
from vertexai.preview.rag import RagCorpus, RagResource

from src.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single chunk returned by the RAG retrieval step."""

    text: str
    source_uri: str
    score: float
    chunk_index: int = 0


@dataclass
class RAGResponse:
    """Full response from the RAG pipeline."""

    query: str
    answer: str
    retrieved_chunks: list[RetrievalResult]
    model: str


class RAGRetriever:
    """Query the Vertex AI RAG corpus and generate grounded answers with Gemini."""

    def __init__(self, settings: Settings, corpus: RagCorpus) -> None:
        self.settings = settings
        self.corpus = corpus
        vertexai.init(project=settings.project_id, location=settings.region)

    # ------------------------------------------------------------------
    # Retrieval-only
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> list[RetrievalResult]:
        """Retrieve relevant chunks from the corpus for *query*.

        Args:
            query: Natural-language question or search string.

        Returns:
            Ordered list of :class:`RetrievalResult` objects (most relevant first).
        """
        response = rag.retrieval_query(
            rag_resources=[
                RagResource(
                    rag_corpus=self.corpus.name,
                    rag_file_ids=[],  # empty = all files
                )
            ],
            text=query,
            similarity_top_k=self.settings.rag_retrieval_top_k,
            vector_distance_threshold=self.settings.rag_vector_distance_threshold,
        )

        results: list[RetrievalResult] = []
        for i, ctx in enumerate(response.contexts.contexts):
            results.append(
                RetrievalResult(
                    text=ctx.text,
                    source_uri=ctx.source_uri,
                    score=ctx.score,
                    chunk_index=i,
                )
            )
        logger.info("Retrieved %d chunks for query: %r", len(results), query[:80])
        return results

    # ------------------------------------------------------------------
    # Retrieval-Augmented Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        query: str,
        system_instruction: Optional[str] = None,
    ) -> RAGResponse:
        """Generate a grounded answer using Gemini with RAG context.

        Args:
            query: Natural-language question.
            system_instruction: Optional system-level instruction for the model.

        Returns:
            A :class:`RAGResponse` with the generated answer and retrieved chunks.
        """
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        RagResource(rag_corpus=self.corpus.name)
                    ],
                    similarity_top_k=self.settings.rag_retrieval_top_k,
                    vector_distance_threshold=self.settings.rag_vector_distance_threshold,
                )
            )
        )

        model_kwargs = {}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        model = GenerativeModel(
            model_name=self.settings.generation_model,
            tools=[rag_retrieval_tool],
            **model_kwargs,
        )

        logger.info(
            "Generating answer with %s for query: %r",
            self.settings.generation_model,
            query[:80],
        )
        response = model.generate_content(query)
        answer_text = response.text if hasattr(response, "text") else str(response)

        # Also do a direct retrieval so we can surface sources
        chunks = self.retrieve(query)

        return RAGResponse(
            query=query,
            answer=answer_text,
            retrieved_chunks=chunks,
            model=self.settings.generation_model,
        )

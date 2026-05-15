"""RAG engine adapter facade.

RAGAnything/LightRAG is the only supported literature RAG engine in this app.
"""

from .manager import (
    answer_with_raganything_if_configured,
    get_geo_rag_engine_status,
    index_document_with_primary_engine,
    normalized_geo_rag_engine,
)

__all__ = [
    "answer_with_raganything_if_configured",
    "get_geo_rag_engine_status",
    "index_document_with_primary_engine",
    "normalized_geo_rag_engine",
]

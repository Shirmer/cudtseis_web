from .raganything import RAGAnything as RAGAnything
from .config import RAGAnythingConfig as RAGAnythingConfig

__version__ = "1.2.9"
__author__ = "Zirui Guo"
__url__ = "https://github.com/HKUDS/RAG-Anything"

__all__ = ["RAGAnything", "RAGAnythingConfig"]


from raganything.literature.models import Author, Paper
from raganything.literature.search import search_papers
from raganything.literature.verify import (
    CitationResult,
    VerificationReport,
    VerifyStatus,
    verify_citations,
)

__all__ = [
    "RAGAnything", 
    "RAGAnythingConfig",
    "Author",
    "CitationResult",
    "Paper",
    "VerificationReport",
    "VerifyStatus",
    "search_papers",
    "verify_citations",
]
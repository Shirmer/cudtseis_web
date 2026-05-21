"""
Compatibility facade for literature retrieval and synthesis.

The implementation now lives in dedicated modules so higher-level services can
depend on smaller units without importing the old monolithic module.
"""

from .literature_search import build_event_queries, search_related_papers
from .literature_synthesis import synthesize_event_and_literature

__all__ = [
    "build_event_queries",
    "search_related_papers",
    "synthesize_event_and_literature",
]

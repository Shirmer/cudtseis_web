# -*- coding: utf-8 -*-

"""
In-memory cache for graph stats.
Avoids reading 900MB+ JSON files on every /stats request.
"""

import time

_graph_stats_cache = {"data": None, "time": 0, "ttl": 300}  # 5 min TTL


def invalidate_graph_stats():
    """Clear graph stats cache (call after document indexing)."""
    _graph_stats_cache["data"] = None
    _graph_stats_cache["time"] = 0


def get_cached_graph_stats():
    """Get cached stats if valid, returns None if expired."""
    now = time.time()
    if _graph_stats_cache["data"] and now - _graph_stats_cache["time"] < _graph_stats_cache["ttl"]:
        return _graph_stats_cache["data"]
    return None


def set_cached_graph_stats(data):
    """Cache graph stats."""
    _graph_stats_cache["data"] = data
    _graph_stats_cache["time"] = time.time()

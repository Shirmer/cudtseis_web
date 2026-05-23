# External Reference Notes

This folder is now only a lightweight methodology reference. Runtime code no longer imports anything from `references/`.

The project uses the complete upstream `rag-system/RAG-Anything/` source tree as the RAG engine layer. ResearchClaw and literature-review ideas are kept only as design notes for future evidence review, knowledge cards, search strategy, and audit trail work.

## Current Runtime Rule

- RAG engine: `rag-system/RAG-Anything/` plus installed LightRAG/MinerU dependencies.
- Product layer: `Project-Code/backend/app`.
- Reference notes: `references/`, read-only for humans.
- Removed direction: old Agent-RAG snapshots, old self-built vector fallback, and MVP-only planning files.

## Developer Command

Use one setup command for the current RAGAnything direction:

```bash
python dev.py setup-raganything
python dev.py
```

For frontend-only or non-RAG work, `python dev.py` is still enough if dependencies already exist locally.

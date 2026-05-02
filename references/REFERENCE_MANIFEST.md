# External RAG Reference Snapshot

This folder keeps a lightweight reference snapshot from the imported `Agent-RAG` and `AutoResearchClaw` folders.

The original folders were useful for reading architecture and implementation ideas, but they also contained local virtual environments, Node dependencies, generated parsing output, sample PDFs, caches, and nested Git history. Those files are not required for this project to run and make collaboration painful.

## What Was Kept

- `Agent-RAG`: RAGAnything-style parsing, multimodal document processing, query, prompt, and literature helper code.
- `AutoResearchClaw`: ResearchClaw-style pipeline contracts, stage orchestration, literature verification, HITL review, and knowledge graph references.
- `literature-review`: systematic literature-review workflow, database search strategy, citation verification, deduplication/ranking, and report template references.
- Selected tests that explain intended behavior for ResearchClaw contracts, stages, literature, HITL, and knowledge graph code.

See `REFERENCE_FILES.txt` for the exact source files copied into `source-snapshots/`.

## What Can Be Removed From The Original Imports

After this snapshot is created, the original imported `Agent-RAG`, `AutoResearchClaw`, and `literature-review` folders can be deleted from the project root. The parts below are not needed for this project to run:

- Python virtual environments such as `Agent-RAG/.venv`.
- Frontend dependency folders such as `Agent-RAG/rag-frontend/node_modules`.
- Local npm/pip caches.
- Generated parser output under `Agent-RAG/output`.
- Local vector storage under `Agent-RAG/rag_storage`.
- Sample PDFs under `Agent-RAG/rag_pdfs`.
- Nested `.git` directories from imported repositories.
- Demo websites, screenshots, generated paper PDFs, and other showcase artifacts not needed for our MVP.
- Standalone skill folders that are useful only as design references after their core files have been copied into `source-snapshots/`.

## How To Use This Snapshot

Do not import this code directly into the running app. Treat it as design reference while implementing adapters in `Project-Code/backend/app`.

For MVP collaboration, run only:

```bash
python dev.py setup
python dev.py
```

Only install optional stacks when you are assigned that area:

```bash
python dev.py setup-qdrant
python dev.py setup-raganything
```

Default development should stay lightweight and reproducible.

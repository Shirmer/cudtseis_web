# Literature Review Reference Notes

`literature-review` is useful to this project as a methodology and tooling reference, not as a runtime dependency.

## Useful Parts

- `SKILL.md`: A complete systematic-review workflow, including planning, multi-database search, screening, quality assessment, thematic synthesis, citation verification, and report generation.
- `references/database_strategies.md`: Search strategy patterns for PubMed, arXiv, Semantic Scholar, OpenAlex, citation chaining, deduplication, and evidence prioritization.
- `assets/review_template.md`: A structured review/report template that can guide our future AI-generated literature analysis reports.
- `scripts/search_databases.py`: Simple reference implementation for deduplicating paper records by DOI/title, filtering by year, ranking by citations/year/relevance, and producing summaries.
- `scripts/verify_citations.py`: Reference implementation for DOI extraction, DOI resolution, CrossRef metadata lookup, and citation report generation.
- `scripts/generate_pdf.py`: Optional reference for rendering Markdown review outputs to PDF with Pandoc.
- `scripts/generate_schematic*.py`: Optional reference for scientific diagram generation and AI-based quality review. This is not part of the MVP runtime.

## How It Maps To Our RAG System

- Literature ingestion quality gate: use the search, deduplication, DOI verification, and metadata-normalization ideas before adding papers to the knowledge base.
- Evidence reliability scoring: combine citation count, venue quality, publication type, year, DOI validity, and manual/AI screening status.
- Audit trail: preserve search strategy, inclusion/exclusion criteria, screening decisions, and citation verification results as metadata.
- Report generation: use the review template as a future structure for "evidence-backed literature analysis" outputs.

## What Not To Do

- Do not install this folder as a dependency for ordinary development.
- Do not call its web/API scripts from the production backend until they are rewritten as project-owned adapters.
- Do not store generated PDFs, figures, search dumps, or API caches in Git.

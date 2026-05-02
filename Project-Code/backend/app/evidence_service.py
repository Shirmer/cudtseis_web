from __future__ import annotations

from typing import Any


def build_evidence_pack(
    *,
    question: str,
    results: list[dict[str, Any]],
    purpose: str,
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = []
    for index, result in enumerate(results, start=1):
        citation = result.get("citation") or {}
        evidence.append(
            {
                "id": f"E{index}",
                "unitId": result.get("unitId", ""),
                "paperId": result.get("paperId", ""),
                "documentId": result.get("documentId", ""),
                "title": result.get("title", ""),
                "page": result.get("page"),
                "score": round(float(result.get("score", 0.0) or 0.0), 4),
                "citation": _citation_text(citation, result),
                "text": result.get("text", "")[:900],
                "metadata": result.get("metadata", {}),
            }
        )

    limitations = []
    if not evidence:
        limitations.append("No indexed literature evidence was retrieved for this question.")
    if event and not event.get("mag"):
        limitations.append("The earthquake event payload does not include magnitude.")
    if event and event.get("depth_km") is None:
        limitations.append("The earthquake event payload does not include focal depth.")

    confidence = "low"
    if len(evidence) >= 5:
        confidence = "medium-high"
    elif len(evidence) >= 2:
        confidence = "medium"

    return {
        "question": question,
        "purpose": purpose,
        "evidence": evidence,
        "claimPolicy": [
            "Every scientific claim should be grounded in one or more evidence IDs.",
            "Do not infer real-time hazard, casualty, or prediction conclusions from literature alone.",
            "State uncertainty when the retrieved evidence is sparse, generic, or not region-specific.",
        ],
        "confidence": confidence,
        "limitations": limitations,
    }


def _citation_text(citation: dict[str, Any], fallback: dict[str, Any]) -> str:
    title = citation.get("title") or fallback.get("title") or "Untitled"
    authors = citation.get("authors") or fallback.get("metadata", {}).get("authors") or []
    year = citation.get("year") or fallback.get("metadata", {}).get("year") or ""
    doi = citation.get("doi") or fallback.get("metadata", {}).get("doi") or ""
    page = citation.get("page") or fallback.get("page")
    author_text = ", ".join(authors[:2]) if isinstance(authors, list) else str(authors)
    suffix = f", p. {page}" if page else ""
    doi_text = f", DOI: {doi}" if doi else ""
    return f"{author_text}. {title}. {year}{suffix}{doi_text}".strip()

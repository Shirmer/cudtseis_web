from __future__ import annotations

from collections import Counter
from typing import Any


CARD_SCHEMA_VERSION = "knowledge-card-v1"


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


def build_document_knowledge_card(
    *,
    document_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int | None,
    doi: str,
    source_url: str,
    pages: list[dict[str, Any]],
    units: list[dict[str, Any]],
    storage_uri: str,
    parser: str,
) -> dict[str, Any]:
    content_type_counts = Counter(str(unit.get("content_type") or "text") for unit in units)
    section_counts = Counter(str(unit.get("section_role") or "body") for unit in units)
    evidence_counts = Counter(str(unit.get("evidence_role") or "primary") for unit in units)
    tags = _collect_unit_tags(units)
    representative = _representative_snippets(units)
    multimodal_items = _multimodal_items(units)
    text_quality_flags = _text_quality_flags(units)

    card = {
        "cardType": "document",
        "schemaVersion": CARD_SCHEMA_VERSION,
        "documentId": document_id,
        "paperId": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "sourceUrl": source_url,
        "storageUri": storage_uri,
        "parser": parser,
        "researchQuestions": _infer_research_questions(title, representative),
        "studyObjects": tags["topics"][:12],
        "studyAreas": tags["regions"][:12],
        "faultsOrStructures": tags["faults"][:12],
        "methodsOrData": representative["methods"][:5],
        "keyFindings": representative["findings"][:6],
        "limitations": _document_limitations(evidence_counts, text_quality_flags, multimodal_items),
        "multimodalEvidence": {
            "counts": {key: content_type_counts[key] for key in sorted(content_type_counts) if key != "text"},
            "items": multimodal_items[:8],
        },
        "sourceStats": {
            "pages": len(pages),
            "units": len(units),
            "contentTypeCounts": dict(content_type_counts),
            "sectionRoleCounts": dict(section_counts),
            "evidenceRoleCounts": dict(evidence_counts),
        },
        "qualityNotes": text_quality_flags,
    }
    card["searchableText"] = _document_card_text(card)
    return card


def build_question_knowledge_card(
    *,
    question: str,
    evidence_pack: dict[str, Any],
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence_pack.get("evidence", [])
    grouped = _group_evidence_by_document(evidence)
    section_roles = Counter(
        str((item.get("metadata") or {}).get("sectionRole") or "unknown") for item in evidence
    )
    evidence_roles = Counter(
        str((item.get("metadata") or {}).get("evidenceRole") or "primary") for item in evidence
    )
    support_items = _support_items(evidence)
    limitations = list(evidence_pack.get("limitations") or [])
    limitations.extend(_question_limitations(evidence, grouped, evidence_roles))

    return {
        "cardType": "question",
        "schemaVersion": CARD_SCHEMA_VERSION,
        "question": question,
        "eventContext": _compact_event(event),
        "confidence": evidence_pack.get("confidence", "low"),
        "evidenceCount": len(evidence),
        "documentCount": len(grouped),
        "supportingEvidence": support_items,
        "evidenceByDocument": grouped,
        "methodDataSignals": _signals_by_role(evidence, {"methods", "data"}),
        "findingSignals": _signals_by_role(evidence, {"results", "discussion", "conclusion", "body"}),
        "possibleConflicts": _possible_conflicts(grouped),
        "limitations": _dedupe_text(limitations)[:8],
        "diagnostics": {
            "sectionRoleCounts": dict(section_roles),
            "evidenceRoleCounts": dict(evidence_roles),
            "topDocumentShare": _top_document_share(grouped, len(evidence)),
        },
        "answerPolicy": [
            "Use only supportingEvidence IDs when making scientific claims.",
            "Separate direct literature evidence from cautious inference.",
            "Mention uncertainty when evidence is sparse, low quality, or concentrated in one paper.",
        ],
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


def _collect_unit_tags(units: list[dict[str, Any]]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {"topics": [], "regions": [], "faults": []}
    for unit in units:
        tags = unit.get("geo_entities") or unit.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        for key in values:
            raw_items = tags.get(key) or []
            if isinstance(raw_items, list):
                values[key].extend(str(item) for item in raw_items if str(item).strip())
    return {key: _dedupe_text(items) for key, items in values.items()}


def _representative_snippets(units: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    methods: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for unit in units:
        content_type = str(unit.get("content_type") or "text")
        if content_type != "text":
            continue
        role = str(unit.get("section_role") or "body")
        evidence_role = str(unit.get("evidence_role") or "primary")
        if evidence_role == "low-evidence":
            continue
        snippet = _snippet(str(unit.get("text") or ""), 320)
        if not snippet:
            continue
        item = {
            "page": unit.get("page"),
            "section": unit.get("section", ""),
            "sectionRole": role,
            "text": snippet,
        }
        if role in {"methods", "data"}:
            methods.append(item)
        if role in {"results", "discussion", "conclusion", "body"}:
            findings.append(item)
    if not findings:
        findings = methods[:3]
    return {"methods": methods, "findings": findings}


def _multimodal_items(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for unit in units:
        content_type = str(unit.get("content_type") or "text")
        if content_type == "text":
            continue
        modality = unit.get("modality") or {}
        items.append(
            {
                "contentType": content_type,
                "page": unit.get("page"),
                "caption": _snippet(str(unit.get("text") or ""), 260),
                "bbox": unit.get("bbox") or {},
                "parser": modality.get("parser") if isinstance(modality, dict) else "",
            }
        )
    return items


def _text_quality_flags(units: list[dict[str, Any]]) -> list[str]:
    flags = []
    if any((unit.get("text_quality") or {}).get("lineJoinRisk", 0) > 0.5 for unit in units):
        flags.append("possible_pdf_text_joining_noise")
    if any(str(unit.get("language") or "") == "unknown" for unit in units):
        flags.append("some_units_have_unknown_language")
    return flags


def _document_limitations(
    evidence_counts: Counter[str],
    text_quality_flags: list[str],
    multimodal_items: list[dict[str, Any]],
) -> list[str]:
    limitations = []
    if evidence_counts.get("low-evidence", 0):
        limitations.append("Reference, acknowledgement, or funding sections are stored but downweighted for claims.")
    if text_quality_flags:
        limitations.append("Some extracted text may require source-page verification before strong claims.")
    if not multimodal_items:
        limitations.append("No structured figure, table, or equation candidates were extracted from this document.")
    return limitations


def _document_card_text(card: dict[str, Any]) -> str:
    parts = [
        str(card.get("title") or ""),
        " ".join(card.get("studyObjects") or []),
        " ".join(card.get("studyAreas") or []),
        " ".join(card.get("faultsOrStructures") or []),
    ]
    for section in ("researchQuestions", "methodsOrData", "keyFindings", "limitations"):
        for item in card.get(section) or []:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
    return "\n".join(part for part in parts if part.strip())


def _infer_research_questions(title: str, representative: dict[str, list[dict[str, Any]]]) -> list[str]:
    questions = []
    clean_title = title.strip()
    if clean_title:
        questions.append(f"What geoscientific problem does this paper address: {clean_title}?")
    for item in representative.get("methods", [])[:2]:
        text = item.get("text", "")
        if text:
            questions.append(f"What data or method is used near p.{item.get('page') or '-'}?")
    return questions[:4]


def _group_evidence_by_document(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in evidence:
        document_id = str(item.get("documentId") or "")
        if document_id not in grouped:
            grouped[document_id] = {
                "documentId": document_id,
                "paperId": item.get("paperId", ""),
                "title": item.get("title", ""),
                "evidenceIds": [],
                "pages": [],
                "bestScore": 0.0,
            }
        group = grouped[document_id]
        group["evidenceIds"].append(item.get("id", ""))
        page = item.get("page")
        if page and page not in group["pages"]:
            group["pages"].append(page)
        group["bestScore"] = max(float(group["bestScore"]), float(item.get("score", 0.0) or 0.0))
    return list(grouped.values())


def _support_items(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for item in evidence[:10]:
        metadata = item.get("metadata") or {}
        items.append(
            {
                "evidenceId": item.get("id", ""),
                "documentId": item.get("documentId", ""),
                "page": item.get("page"),
                "score": item.get("score", 0.0),
                "sectionRole": metadata.get("sectionRole", "unknown"),
                "evidenceRole": metadata.get("evidenceRole", "primary"),
                "claimText": _snippet(str(item.get("text") or ""), 260),
            }
        )
    return items


def _signals_by_role(evidence: list[dict[str, Any]], roles: set[str]) -> list[dict[str, Any]]:
    signals = []
    for item in evidence:
        metadata = item.get("metadata") or {}
        role = str(metadata.get("sectionRole") or "body")
        if role not in roles:
            continue
        signals.append(
            {
                "evidenceId": item.get("id", ""),
                "page": item.get("page"),
                "text": _snippet(str(item.get("text") or ""), 220),
            }
        )
    return signals[:6]


def _question_limitations(
    evidence: list[dict[str, Any]],
    grouped: list[dict[str, Any]],
    evidence_roles: Counter[str],
) -> list[str]:
    limitations = []
    if evidence and len(grouped) <= 1:
        limitations.append("Retrieved evidence is concentrated in one document, so cross-paper agreement is not established.")
    if evidence_roles.get("low-evidence", 0):
        limitations.append("Some selected evidence comes from low-evidence sections and should be verified in source context.")
    if len(evidence) < 3:
        limitations.append("Evidence count is small; the answer should remain tentative.")
    return limitations


def _possible_conflicts(grouped: list[dict[str, Any]]) -> list[str]:
    if len(grouped) < 2:
        return []
    return ["No explicit contradiction was detected automatically; compare evidence across documents before strong synthesis."]


def _top_document_share(grouped: list[dict[str, Any]], evidence_count: int) -> float:
    if not grouped or evidence_count <= 0:
        return 0.0
    return round(max(len(group["evidenceIds"]) for group in grouped) / evidence_count, 4)


def _compact_event(event: dict[str, Any] | None) -> dict[str, Any]:
    if not event:
        return {}
    return {
        "id": event.get("id"),
        "place": event.get("place"),
        "mag": event.get("mag"),
        "depthKm": event.get("depth_km"),
        "time": event.get("time"),
    }


def _snippet(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def _dedupe_text(items: list[Any]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        text = str(item).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output

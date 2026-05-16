from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventOut(BaseModel):
    id: str
    time: str
    updated: str
    mag: float | None
    place: str | None
    depth_km: float | None
    lon: float
    lat: float
    magType: str | None = None
    nst: int | None = None
    gap: float | None = None
    dmin: float | None = None
    rms: float | None = None
    net: str | None = None
    type: str | None = None
    horizontalError: float | None = None
    depthError: float | None = None
    magError: float | None = None
    magNst: int | None = None
    status: str | None = None
    locationSource: str | None = None
    magSource: str | None = None


class EventQueryParams(BaseModel):
    minMag: float = 3.0
    maxMag: float | None = None
    hours: int | None = Field(default=24, ge=1, le=168)
    start: datetime | None = None
    end: datetime | None = None
    minDepth: float | None = None
    maxDepth: float | None = None
    bbox: str | None = None
    minLon: float | None = None
    maxLon: float | None = None
    minLat: float | None = None
    maxLat: float | None = None
    limit: int = Field(default=5000, ge=1, le=20000)
    offset: int = Field(default=0, ge=0)


class EventsPageOut(BaseModel):
    items: list[EventOut]
    total: int
    limit: int
    offset: int
    hasMore: bool


class PaperOut(BaseModel):
    paperId: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    authorsText: str | None = None
    year: int | None = None
    abstract: str | None = None
    abstractPreview: str | None = None
    evidenceSnippet: str | None = None
    venue: str | None = None
    citationCount: int | None = None
    doi: str | None = None
    url: str | None = None
    source: str | None = None
    relevanceHint: str | None = None


class PaperDatabaseItemOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    authorsText: str
    journal: str
    year: int
    doi: str
    url: str
    topics: list[str]
    evidenceType: str
    abstractPreview: str
    parserStatus: dict[str, str]
    cer: dict[str, str]
    relations: list[dict[str, str]]
    retrievalScore: float = 0.0
    retrievalBreakdown: dict[str, float] = Field(default_factory=dict)
    metadataDecision: dict[str, Any] = Field(default_factory=dict)
    evidencePack: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    professionalInterpretation: dict[str, Any] = Field(default_factory=dict)


class PaperChunkOut(BaseModel):
    type: str
    content: str
    ordinal: int


class PaperDetailOut(PaperDatabaseItemOut):
    chunks: list[PaperChunkOut] = Field(default_factory=list)


class PaperCreateRequest(BaseModel):
    id: str | None = None
    title: str = Field(..., min_length=1, max_length=500)
    authors: list[str] = Field(..., min_length=1)
    journal: str = Field(..., min_length=1, max_length=200)
    year: int = Field(..., ge=1900, le=2100)
    doi: str = ""
    url: str = ""
    topics: list[str] = Field(..., min_length=1)
    evidenceType: str = "Manual"
    abstractPreview: str = Field(..., min_length=1, max_length=3000)
    claim: str = Field(..., min_length=1, max_length=2000)
    evidence: str = Field(..., min_length=1, max_length=3000)
    reasoning: str = Field(..., min_length=1, max_length=3000)


class PaperStorageOut(BaseModel):
    path: str
    papers: int
    topics: int
    chunks: int
    relations: int
    sizeBytes: int
    status: str


class PaperArchitectureOut(BaseModel):
    name: str
    pipeline: list[dict[str, str]]
    parserSlots: list[str]
    retrievalModes: list[str]
    storageUnits: list[str]
    structuredFields: list[str]
    generationSchema: list[str]
    validationChecks: list[str]


class PaperDatabaseResponseOut(BaseModel):
    query: str
    filters: dict[str, Any]
    total: int
    items: list[PaperDatabaseItemOut]
    topicCounts: dict[str, int]
    yearRange: dict[str, int]
    architecture: PaperArchitectureOut
    queryPlan: dict[str, Any]
    generatedAt: str


class TopicSignalOut(BaseModel):
    key: str
    label: str
    description: str
    paperCount: int


class SummarySectionOut(BaseModel):
    key: str
    title: str
    paragraphs: list[str]


class SummaryOut(BaseModel):
    headline: str
    subtitle: str
    abstract: str
    sections: list[SummarySectionOut]
    keyPoints: list[str]
    evidenceCards: list[dict[str, str]]
    closing: str
    limitations: str


class ResearchResponseOut(BaseModel):
    event: EventOut
    cohort: dict[str, Any]
    topicSignals: list[TopicSignalOut]
    summary: SummaryOut
    papers: list[PaperOut]
    queryPlan: dict[str, Any]
    sourceBreakdown: dict[str, int]
    notes: list[str]
    mode: str
    generatedAt: str


class EventRagRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    hours: int = Field(default=24, ge=1, le=168)
    minMag: float = Field(default=3.0)
    cohortLimit: int = Field(default=5000, ge=1, le=20000)
    paperLimit: int = Field(default=12, ge=1, le=20)
    yearMin: int = Field(default=2015, ge=1990, le=2100)
    topK: int = Field(default=6, ge=1, le=12)


class RagQueryRequest(EventRagRequest):
    eventId: str | None = None


class RetrievedContextOut(BaseModel):
    id: str
    sourceType: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagResponseOut(BaseModel):
    question: str
    answer: str
    retrievedContexts: list[RetrievedContextOut]
    contextCount: int
    retrievalMode: str
    suggestedQuestions: list[str]
    event: EventOut
    generatedAt: str
    mode: str


class KnowledgeInitOut(BaseModel):
    status: str
    backend: str
    collection: str
    vectorSize: int
    documents: int
    units: int
    knowledgeCards: int = 0
    indexVersion: str
    storageBackend: str = "local"
    ragEngine: dict[str, Any] = Field(default_factory=dict)
    message: str
    warning: str = ""
    generatedAt: str


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=3000)
    topK: int = Field(default=8, ge=1, le=30)
    paperId: str | None = Field(default=None, max_length=200)
    documentId: str | None = Field(default=None, max_length=200)
    contentType: str | None = Field(default=None, max_length=40)
    regions: list[str] = Field(default_factory=list)
    faults: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class KnowledgeHitOut(BaseModel):
    unitId: str
    documentId: str
    paperId: str
    title: str
    contentType: str
    text: str
    page: int | None = None
    score: float
    citation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchOut(BaseModel):
    query: str
    topK: int
    filters: dict[str, Any]
    backend: str
    collection: str
    warning: str = ""
    embeddingBackend: str
    results: list[KnowledgeHitOut]
    generatedAt: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    storeStats: dict[str, int]


class KnowledgeContextItemOut(BaseModel):
    unitId: str
    documentId: str
    paperId: str
    title: str
    contentType: str
    text: str
    page: int | None = None
    unitIndex: int
    position: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeContextOut(BaseModel):
    unitId: str
    documentId: str
    paperId: str
    title: str
    page: int | None = None
    fileName: str = ""
    sourceAvailable: bool = False
    items: list[KnowledgeContextItemOut]


class DocumentIngestRequest(BaseModel):
    filePath: str = Field(..., min_length=1, max_length=1000)
    paperId: str | None = Field(default=None, max_length=200)
    documentId: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1500, le=2200)
    doi: str | None = Field(default=None, max_length=200)
    sourceUrl: str | None = Field(default=None, max_length=1000)
    parser: str | None = Field(default=None, max_length=80)
    force: bool = False


class DocumentIngestOut(BaseModel):
    documentId: str
    paperId: str
    title: str
    status: str
    parser: str
    pages: int
    units: int
    multimodalUnits: int = 0
    storageUri: str = ""
    fileSha256: str
    vectorStore: dict[str, Any]
    embeddingBackend: str
    ragEngine: dict[str, Any] = Field(default_factory=dict)
    knowledgeCard: dict[str, Any] = Field(default_factory=dict)
    message: str


class DocumentBatchIngestRequest(BaseModel):
    directoryPath: str = Field(..., min_length=1, max_length=1000)
    recursive: bool = False
    force: bool = False
    limit: int = Field(default=100, ge=1, le=1000)
    extensions: list[str] = Field(default_factory=lambda: [".pdf", ".txt", ".md"])


class DocumentBatchIngestItemOut(BaseModel):
    id: str = ""
    filePath: str
    status: str
    documentId: str = ""
    paperId: str = ""
    title: str = ""
    pages: int = 0
    units: int = 0
    multimodalUnits: int = 0
    storageUri: str = ""
    embeddingBackend: str = ""
    ragEngine: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error: str = ""
    startedAt: str = ""
    finishedAt: str = ""


class DocumentBatchIngestOut(BaseModel):
    jobId: str = ""
    directoryPath: str
    recursive: bool
    force: bool = False
    limit: int
    status: str = "queued"
    progress: float = 0.0
    total: int
    queued: int = 0
    running: int = 0
    succeeded: int
    skipped: int
    failed: int
    message: str = ""
    items: list[DocumentBatchIngestItemOut]
    createdAt: str = ""
    startedAt: str = ""
    finishedAt: str = ""
    generatedAt: str


class DocumentStatusOut(BaseModel):
    documentId: str
    paperId: str
    title: str
    status: str
    parser: str
    pages: int
    units: int
    fileSha256: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: str
    updatedAt: str


class RagAnythingDocumentRequest(BaseModel):
    filePath: str = Field(..., min_length=1, max_length=1000)
    docId: str | None = Field(default=None, max_length=300)
    parseMethod: str | None = Field(default=None, max_length=30)
    parser: str | None = Field(default=None, max_length=30)


class RagAnythingEventIngestRequest(BaseModel):
    eventId: str
    hours: int = Field(default=24, ge=1, le=168)
    minMag: float = Field(default=3.0)
    cohortLimit: int = Field(default=5000, ge=1, le=20000)
    paperLimit: int = Field(default=12, ge=1, le=20)
    yearMin: int = Field(default=2015, ge=1990, le=2100)
    force: bool = False


class RagAnythingQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    mode: str | None = Field(default=None, max_length=30)
    vlmEnhanced: bool | None = None
    onlyNeedPrompt: bool = False


class RagAnythingStatusOut(BaseModel):
    enabled: bool
    available: bool
    ready: bool = False
    reason: str
    engineMode: str = "raganything"
    workingDir: str
    outputDir: str
    documentDir: str
    allowedDocumentRoots: list[str] = Field(default_factory=list)
    parser: str
    parseMethod: str
    allowParseFallback: bool = False
    parseFallbackMethod: str = ""
    queryMode: str
    allowQueryFallback: bool = False
    queryFallbackMode: str = ""
    dependencies: dict[str, Any] = Field(default_factory=dict)
    sourceSnapshot: dict[str, Any] = Field(default_factory=dict)
    requiredActions: list[str] = Field(default_factory=list)


class RagAnythingIngestOut(BaseModel):
    status: str
    mode: str
    documents: int = 0
    storePath: str
    outputDir: str = ""
    contentStats: dict[str, Any] = Field(default_factory=dict)
    message: str


class RagAnythingQueryOut(BaseModel):
    status: str = "ready"
    question: str
    answer: str
    retrievalMode: str
    queryMode: str = ""
    mode: str
    attemptedQueryModes: list[str] = Field(default_factory=list)
    queryFallback: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepOut(BaseModel):
    key: str
    title: str
    description: str
    status: str


class ResearchWorkflowOut(BaseModel):
    event: EventOut
    generatedAt: str
    workflow: list[WorkflowStepOut]
    papers: list[PaperOut]
    topicSignals: list[TopicSignalOut]


class VectorIndexOut(BaseModel):
    eventId: str
    documents: int
    retrievalMode: str
    storePath: str

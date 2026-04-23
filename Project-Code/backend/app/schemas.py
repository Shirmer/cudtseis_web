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

from __future__ import annotations

import asyncio
import json

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import SessionLocal, engine, get_db
from .event_service import query_events_page, query_events_payload
from .ingest import fetch_usgs_geojson, upsert_and_get_new
from .paper_database import add_paper, get_paper_architecture, get_paper_detail, initialize_paper_database, search_papers
from .rag import answer_event_question, prepare_event_vector_index
from .raganything_service import (
    get_raganything_status,
    ingest_document_with_raganything,
    ingest_event_bundle_with_raganything,
    query_raganything as query_raganything_service,
)
from .research_service import build_event_research_bundle
from .schemas import (
    EventOut,
    EventQueryParams,
    EventRagRequest,
    EventsPageOut,
    PaperArchitectureOut,
    PaperCreateRequest,
    PaperDatabaseResponseOut,
    PaperDetailOut,
    PaperStorageOut,
    RagAnythingDocumentRequest,
    RagAnythingEventIngestRequest,
    RagAnythingIngestOut,
    RagAnythingQueryOut,
    RagAnythingQueryRequest,
    RagAnythingStatusOut,
    RagQueryRequest,
    RagResponseOut,
    ResearchResponseOut,
    ResearchWorkflowOut,
    VectorIndexOut,
)
from .settings import settings
from .models import Base


subscribers: set[asyncio.Queue] = set()


def parse_cors_origins(raw: str) -> list[str]:
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://127.0.0.1:5173", "http://localhost:5173"]


def create_app(*, create_tables: bool = True, enable_poller: bool = True) -> FastAPI:
    app = FastAPI(title="QuakeViz")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if create_tables:
        try:
            Base.metadata.create_all(bind=engine)
        except SQLAlchemyError as exc:
            print("database initialization skipped:", exc)
    initialize_paper_database()

    @app.get("/")
    def root():
        return {
            "service": "QuakeViz backend",
            "status": "ok",
            "docs": "/docs",
            "eventsApi": "/api/events",
            "papersApi": "/api/papers",
            "streamApi": "/api/stream",
        }

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    if enable_poller:
        @app.on_event("startup")
        async def startup():
            asyncio.create_task(poller())

    @app.get("/api/events", response_model=list[EventOut])
    def list_events(
        db: Session = Depends(get_db),
        minMag: float = Query(3.0),
        maxMag: float | None = Query(None),
        hours: int | None = Query(24, ge=1, le=168),
        start: str | None = Query(None),
        end: str | None = Query(None),
        minDepth: float | None = Query(None),
        maxDepth: float | None = Query(None),
        bbox: str | None = Query(None, description="west,south,east,north"),
        minLon: float | None = Query(None),
        maxLon: float | None = Query(None),
        minLat: float | None = Query(None),
        maxLat: float | None = Query(None),
        limit: int = Query(5000, ge=1, le=20000),
    ):
        params = EventQueryParams(
            minMag=minMag,
            maxMag=maxMag,
            hours=hours,
            start=start,
            end=end,
            minDepth=minDepth,
            maxDepth=maxDepth,
            bbox=bbox,
            minLon=minLon,
            maxLon=maxLon,
            minLat=minLat,
            maxLat=maxLat,
            limit=limit,
        )
        return query_events_payload(db, **params.model_dump())

    @app.get("/api/events/search", response_model=EventsPageOut)
    def search_events(
        db: Session = Depends(get_db),
        minMag: float = Query(3.0),
        maxMag: float | None = Query(None),
        hours: int | None = Query(24, ge=1, le=168),
        start: str | None = Query(None),
        end: str | None = Query(None),
        minDepth: float | None = Query(None),
        maxDepth: float | None = Query(None),
        bbox: str | None = Query(None),
        minLon: float | None = Query(None),
        maxLon: float | None = Query(None),
        minLat: float | None = Query(None),
        maxLat: float | None = Query(None),
        limit: int = Query(5000, ge=1, le=20000),
        offset: int = Query(0, ge=0),
    ):
        params = EventQueryParams(
            minMag=minMag,
            maxMag=maxMag,
            hours=hours,
            start=start,
            end=end,
            minDepth=minDepth,
            maxDepth=maxDepth,
            bbox=bbox,
            minLon=minLon,
            maxLon=maxLon,
            minLat=minLat,
            maxLat=maxLat,
            limit=limit,
            offset=offset,
        )
        return query_events_page(db, params)

    @app.get("/api/events/{event_id}/research", response_model=ResearchResponseOut)
    def get_event_research(
        event_id: str,
        db: Session = Depends(get_db),
        hours: int = Query(24, ge=1, le=168),
        minMag: float = Query(3.0),
        cohortLimit: int = Query(5000, ge=1, le=20000),
        paperLimit: int = Query(12, ge=1, le=20),
        yearMin: int = Query(2015, ge=1990, le=2100),
    ):
        bundle = build_event_research_bundle(
            db,
            event_id=event_id,
            hours=hours,
            minMag=minMag,
            cohortLimit=cohortLimit,
            paperLimit=paperLimit,
            yearMin=yearMin,
        )
        return {
            "event": bundle["event"],
            "cohort": bundle["synthesis"]["cohort"],
            "topicSignals": bundle["synthesis"]["topicSignals"],
            "summary": bundle["synthesis"]["summary"],
            "papers": bundle["literature"]["papers"],
            "queryPlan": bundle["literature"]["queryPlan"],
            "sourceBreakdown": bundle["literature"]["sourceBreakdown"],
            "notes": bundle["literature"]["notes"],
            "mode": bundle["literature"]["mode"],
            "generatedAt": bundle["literature"]["generatedAt"],
        }

    @app.get("/api/papers/architecture", response_model=PaperArchitectureOut)
    def get_papers_architecture():
        return get_paper_architecture()

    @app.get("/api/papers/storage", response_model=PaperStorageOut)
    def get_papers_storage():
        return initialize_paper_database()

    @app.get("/api/papers", response_model=PaperDatabaseResponseOut)
    def list_papers(
        q: str = Query("", max_length=500),
        topic: str = Query("", max_length=100),
        yearMin: int | None = Query(None, ge=1900, le=2100),
        yearMax: int | None = Query(None, ge=1900, le=2100),
        limit: int = Query(20, ge=1, le=100),
    ):
        return search_papers(
            query=q,
            topic=topic,
            year_min=yearMin,
            year_max=yearMax,
            limit=limit,
        )

    @app.get("/api/papers/{paper_id}", response_model=PaperDetailOut)
    def get_paper(paper_id: str):
        paper = get_paper_detail(paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        return paper

    @app.post("/api/papers", response_model=PaperDetailOut, status_code=201)
    def create_paper(payload: PaperCreateRequest):
        try:
            return add_paper(payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/events/{event_id}/workflow", response_model=ResearchWorkflowOut)
    def get_event_workflow(
        event_id: str,
        db: Session = Depends(get_db),
        hours: int = Query(24, ge=1, le=168),
        minMag: float = Query(3.0),
        cohortLimit: int = Query(5000, ge=1, le=20000),
        paperLimit: int = Query(12, ge=1, le=20),
        yearMin: int = Query(2015, ge=1990, le=2100),
    ):
        bundle = build_event_research_bundle(
            db,
            event_id=event_id,
            hours=hours,
            minMag=minMag,
            cohortLimit=cohortLimit,
            paperLimit=paperLimit,
            yearMin=yearMin,
        )
        return {
            "event": bundle["event"],
            "generatedAt": bundle["literature"]["generatedAt"],
            "workflow": bundle["workflow"],
            "papers": bundle["literature"]["papers"],
            "topicSignals": bundle["synthesis"]["topicSignals"],
        }

    @app.post("/api/events/{event_id}/rag", response_model=RagResponseOut)
    def ask_event_rag(
        event_id: str,
        payload: EventRagRequest,
        db: Session = Depends(get_db),
    ):
        bundle = build_event_research_bundle(
            db,
            event_id=event_id,
            hours=payload.hours,
            minMag=payload.minMag,
            cohortLimit=payload.cohortLimit,
            paperLimit=payload.paperLimit,
            yearMin=payload.yearMin,
        )
        rag_response = answer_event_question(
            question=payload.question,
            event=bundle["event"],
            cohort_events=bundle["cohort_events"],
            papers=bundle["literature"]["papers"],
            synthesis=bundle["synthesis"],
            top_k=payload.topK,
        )
        rag_response["event"] = bundle["event"]
        rag_response["generatedAt"] = bundle["literature"]["generatedAt"]
        rag_response["mode"] = "event-rag"
        return rag_response

    @app.post("/api/events/{event_id}/vector-index", response_model=VectorIndexOut)
    def rebuild_event_vector_index(
        event_id: str,
        force: bool = Query(True),
        db: Session = Depends(get_db),
        hours: int = Query(24, ge=1, le=168),
        minMag: float = Query(3.0),
        cohortLimit: int = Query(5000, ge=1, le=20000),
        paperLimit: int = Query(12, ge=1, le=20),
        yearMin: int = Query(2015, ge=1990, le=2100),
    ):
        bundle = build_event_research_bundle(
            db,
            event_id=event_id,
            hours=hours,
            minMag=minMag,
            cohortLimit=cohortLimit,
            paperLimit=paperLimit,
            yearMin=yearMin,
        )
        return prepare_event_vector_index(
            event=bundle["event"],
            cohort_events=bundle["cohort_events"],
            papers=bundle["literature"]["papers"],
            synthesis=bundle["synthesis"],
            force_rebuild=force,
        )

    @app.get("/api/raganything/status", response_model=RagAnythingStatusOut)
    def get_raganything_runtime_status():
        return get_raganything_status()

    @app.post("/api/raganything/events", response_model=RagAnythingIngestOut)
    async def ingest_event_into_raganything(
        payload: RagAnythingEventIngestRequest,
        db: Session = Depends(get_db),
    ):
        bundle = build_event_research_bundle(
            db,
            event_id=payload.eventId,
            hours=payload.hours,
            minMag=payload.minMag,
            cohortLimit=payload.cohortLimit,
            paperLimit=payload.paperLimit,
            yearMin=payload.yearMin,
        )
        return await ingest_event_bundle_with_raganything(
            event=bundle["event"],
            cohort_events=bundle["cohort_events"],
            papers=bundle["literature"]["papers"],
            synthesis=bundle["synthesis"],
            force=payload.force,
        )

    @app.post("/api/raganything/documents", response_model=RagAnythingIngestOut)
    async def ingest_document_into_raganything(payload: RagAnythingDocumentRequest):
        return await ingest_document_with_raganything(
            file_path=payload.filePath,
            doc_id=payload.docId,
            parse_method=payload.parseMethod,
            parser=payload.parser,
        )

    @app.post("/api/raganything/query", response_model=RagAnythingQueryOut)
    async def ask_raganything(payload: RagAnythingQueryRequest):
        return await query_raganything_service(
            question=payload.question,
            mode=payload.mode,
            vlm_enhanced=payload.vlmEnhanced,
        )

    @app.post("/api/rag/query", response_model=RagResponseOut)
    def query_rag(
        payload: RagQueryRequest,
        db: Session = Depends(get_db),
    ):
        if payload.eventId:
            return ask_event_rag(payload.eventId, EventRagRequest(**payload.model_dump(exclude={"eventId"})), db)

        events = query_events_payload(db, minMag=payload.minMag, hours=payload.hours, limit=1)
        if not events:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="No earthquake events available for RAG query")

        selected_event = events[0]
        bundle = build_event_research_bundle(
            db,
            event_id=selected_event["id"],
            hours=payload.hours,
            minMag=payload.minMag,
            cohortLimit=payload.cohortLimit,
            paperLimit=payload.paperLimit,
            yearMin=payload.yearMin,
        )
        rag_response = answer_event_question(
            question=payload.question,
            event=bundle["event"],
            cohort_events=bundle["cohort_events"],
            papers=bundle["literature"]["papers"],
            synthesis=bundle["synthesis"],
            top_k=payload.topK,
        )
        rag_response["event"] = bundle["event"]
        rag_response["generatedAt"] = bundle["literature"]["generatedAt"]
        rag_response["mode"] = "event-rag-latest-event"
        return rag_response

    @app.get("/api/stream")
    async def stream():
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        subscribers.add(q)

        async def gen():
            try:
                yield ": connected\n\n"
                while True:
                    msg = await q.get()
                    data = json.dumps(msg, ensure_ascii=False)
                    yield f"event: {msg['type']}\n"
                    yield f"data: {data}\n\n"
            finally:
                subscribers.discard(q)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


async def poller():
    while True:
        try:
            geojson = fetch_usgs_geojson()
            with SessionLocal() as db:
                new_items = upsert_and_get_new(db, geojson)
            if new_items:
                payload = {"type": "new_events", "data": new_items}
                dead: list[asyncio.Queue] = []
                for q in subscribers:
                    try:
                        q.put_nowait(payload)
                    except Exception:
                        dead.append(q)
                for q in dead:
                    subscribers.discard(q)
        except Exception as exc:
            print("poller error:", exc)
        await asyncio.sleep(settings.poll_seconds)

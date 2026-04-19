'''
REST + SSE + 后台轮询任务
CORS : 后端需要允许前端域名访问（fastapi.middleware.cors 配置）
'''

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from geoalchemy2.functions import ST_X, ST_Y
from fastapi.middleware.cors import CORSMiddleware


from .db import get_db, engine, SessionLocal
from .models import Base, Earthquake
from .ingest import fetch_usgs_geojson, upsert_and_get_new
from .literature import search_related_papers, synthesize_event_and_literature
from .settings import settings


"""
REST + SSE + 后台轮询任务
"""

app = FastAPI(title="QuakeViz")


def parse_cors_origins(raw: str) -> list[str]:
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    if origins:
        return origins
    return ["http://127.0.0.1:5173", "http://localhost:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

EVENT_COLUMNS = (
    Earthquake.id,
    Earthquake.time,
    Earthquake.updated,
    Earthquake.mag,
    Earthquake.place,
    Earthquake.depth_km,
    ST_X(Earthquake.geom).label("lon"),
    ST_Y(Earthquake.geom).label("lat"),
    Earthquake.mag_type,
    Earthquake.nst,
    Earthquake.gap,
    Earthquake.dmin,
    Earthquake.rms,
    Earthquake.net,
    Earthquake.type.label("event_type"),
    Earthquake.horizontal_error,
    Earthquake.depth_error,
    Earthquake.mag_error,
    Earthquake.mag_nst,
    Earthquake.status,
    Earthquake.location_source,
    Earthquake.mag_source,
)

# 简易 SSE 订阅者队列（单机版）
subscribers: set[asyncio.Queue] = set()

@app.on_event("startup")
async def startup():
    asyncio.create_task(poller())

async def poller():
    while True:
        try:
            geojson = fetch_usgs_geojson()
            with SessionLocal() as db:
                new_items = upsert_and_get_new(db, geojson)

            if new_items:
                payload = {"type": "new_events", "data": new_items}
                dead = []
                for q in subscribers:
                    try:
                        q.put_nowait(payload)
                    except Exception:
                        dead.append(q)
                for q in dead:
                    subscribers.discard(q)
        except Exception as e:
            # 生产建议换日志系统
            print("poller error:", e)

        await asyncio.sleep(settings.poll_seconds)


def serialize_event_row(row) -> dict:
    return {
        "id": row.id,
        "time": row.time.isoformat(),
        "updated": row.updated.isoformat(),
        "mag": row.mag,
        "place": row.place,
        "depth_km": row.depth_km,
        "lon": float(row.lon),
        "lat": float(row.lat),
        "magType": row.mag_type,
        "nst": row.nst,
        "gap": row.gap,
        "dmin": row.dmin,
        "rms": row.rms,
        "net": row.net,
        "type": row.event_type,
        "horizontalError": row.horizontal_error,
        "depthError": row.depth_error,
        "magError": row.mag_error,
        "magNst": row.mag_nst,
        "status": row.status,
        "locationSource": row.location_source,
        "magSource": row.mag_source,
    }


def query_events_payload(
    db: Session,
    *,
    minMag: float = 3.0,
    maxMag: float | None = None,
    hours: int | None = 24,
    start: datetime | None = None,
    end: datetime | None = None,
    minDepth: float | None = None,
    maxDepth: float | None = None,
    bbox: str | None = None,
    minLon: float | None = None,
    maxLon: float | None = None,
    minLat: float | None = None,
    maxLat: float | None = None,
    limit: int = 5000,
) -> list[dict]:
    if start or end:
        if end is None:
            end = datetime.now(tz=timezone.utc)
        if start is None:
            start = end - timedelta(hours=hours or 24)
    else:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(hours=hours or 24)

    stmt = select(*EVENT_COLUMNS).where(
        Earthquake.time >= start,
        Earthquake.time <= end,
        Earthquake.mag >= minMag,
    )

    if maxMag is not None:
        stmt = stmt.where(Earthquake.mag <= maxMag)
    if minDepth is not None:
        stmt = stmt.where(Earthquake.depth_km >= minDepth)
    if maxDepth is not None:
        stmt = stmt.where(Earthquake.depth_km <= maxDepth)

    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        stmt = stmt.where(
            ST_X(Earthquake.geom) >= w,
            ST_X(Earthquake.geom) <= e,
            ST_Y(Earthquake.geom) >= s,
            ST_Y(Earthquake.geom) <= n,
        )
    else:
        if minLon is not None:
            stmt = stmt.where(ST_X(Earthquake.geom) >= minLon)
        if maxLon is not None:
            stmt = stmt.where(ST_X(Earthquake.geom) <= maxLon)
        if minLat is not None:
            stmt = stmt.where(ST_Y(Earthquake.geom) >= minLat)
        if maxLat is not None:
            stmt = stmt.where(ST_Y(Earthquake.geom) <= maxLat)

    stmt = stmt.order_by(Earthquake.time.desc()).limit(limit)
    rows = db.execute(stmt).all()
    return [serialize_event_row(row) for row in rows]


def get_event_payload(db: Session, event_id: str) -> dict | None:
    stmt = select(*EVENT_COLUMNS).where(Earthquake.id == event_id).limit(1)
    row = db.execute(stmt).first()
    if row is None:
        return None
    return serialize_event_row(row)

@app.get("/api/events")
def list_events(
    db: Session = Depends(get_db),

    # 震级
    minMag: float = Query(3.0),
    maxMag: float | None = Query(None),

    # 时间：优先 start/end，否则用 hours
    hours: int | None = Query(24, ge=1, le=168),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),

    # 深度
    minDepth: float | None = Query(None),
    maxDepth: float | None = Query(None),

    # 经纬度：bbox 或 min/max
    bbox: str | None = Query(None, description="west,south,east,north"),
    minLon: float | None = Query(None),
    maxLon: float | None = Query(None),
    minLat: float | None = Query(None),
    maxLat: float | None = Query(None),

    limit: int = Query(5000, ge=1, le=20000),
):
    return query_events_payload(
        db,
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

@app.get("/api/events/{event_id}/research")
def get_event_research(
    event_id: str,
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    minMag: float = Query(3.0),
    cohortLimit: int = Query(5000, ge=1, le=20000),
    paperLimit: int = Query(12, ge=1, le=20),
    yearMin: int = Query(2015, ge=1990, le=2100),
):
    event = get_event_payload(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Earthquake event not found")

    cohort_events = query_events_payload(
        db,
        minMag=minMag,
        hours=hours,
        limit=cohortLimit,
    )
    literature = search_related_papers(
        event,
        limit=paperLimit,
        year_min=yearMin,
        semantic_scholar_api_key=settings.semantic_scholar_api_key,
        openalex_email=settings.openalex_email,
    )
    synthesis = synthesize_event_and_literature(
        event=event,
        cohort_events=cohort_events,
        papers=literature["papers"],
    )

    return {
        "event": event,
        "cohort": synthesis["cohort"],
        "topicSignals": synthesis["topicSignals"],
        "summary": synthesis["summary"],
        "papers": literature["papers"],
        "queryPlan": literature["queryPlan"],
        "sourceBreakdown": literature["sourceBreakdown"],
        "notes": literature["notes"],
        "mode": literature["mode"],
        "generatedAt": literature["generatedAt"],
    }

@app.get("/api/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    subscribers.add(q)

    async def gen():
        try:
            # 初次握手给一条注释，防止某些代理缓冲
            yield ": connected\n\n"
            while True:
                msg = await q.get()
                data = json.dumps(msg, ensure_ascii=False)
                yield f"event: {msg['type']}\n"
                yield f"data: {data}\n\n"
        finally:
            subscribers.discard(q)

    return StreamingResponse(gen(), media_type="text/event-stream")

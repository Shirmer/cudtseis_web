from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from fastapi import HTTPException
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .cache_utils import TTLCache
from .models import Earthquake
from .schemas import EventQueryParams
from .settings import settings


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

EVENT_QUERY_CACHE = TTLCache[dict[str, Any]](ttl_seconds=300)


def serialize_event_row(row: Any) -> dict[str, Any]:
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


def validate_query_ranges(params: EventQueryParams) -> None:
    if params.start and params.end and params.start > params.end:
        raise HTTPException(status_code=400, detail="start must be earlier than or equal to end")
    if params.maxMag is not None and params.minMag > params.maxMag:
        raise HTTPException(status_code=400, detail="minMag must be less than or equal to maxMag")
    if params.minDepth is not None and params.maxDepth is not None and params.minDepth > params.maxDepth:
        raise HTTPException(status_code=400, detail="minDepth must be less than or equal to maxDepth")
    if params.minLon is not None and params.maxLon is not None and params.minLon > params.maxLon:
        raise HTTPException(status_code=400, detail="minLon must be less than or equal to maxLon")
    if params.minLat is not None and params.maxLat is not None and params.minLat > params.maxLat:
        raise HTTPException(status_code=400, detail="minLat must be less than or equal to maxLat")
    if params.bbox:
        parts = [part.strip() for part in params.bbox.split(",")]
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="bbox must be formatted as west,south,east,north")
        try:
            west, south, east, north = [float(part) for part in parts]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="bbox contains non-numeric values") from exc
        if west > east or south > north:
            raise HTTPException(status_code=400, detail="bbox must satisfy west<=east and south<=north")


def get_event_payload(db: Session, event_id: str) -> dict[str, Any] | None:
    stmt = select(*EVENT_COLUMNS).where(Earthquake.id == event_id).limit(1)
    row = db.execute(stmt).first()
    if row is None:
        return None
    return serialize_event_row(row)


def query_events_payload(db: Session, **kwargs: Any) -> list[dict[str, Any]]:
    params = EventQueryParams(**kwargs)
    validate_query_ranges(params)
    return query_events_page(db, params)["items"]


def query_events_page(db: Session, params: EventQueryParams) -> dict[str, Any]:
    validate_query_ranges(params)
    cache_key = _events_cache_key(params)
    cached = EVENT_QUERY_CACHE.get(cache_key)
    if cached is not None:
        return cached

    start, end = _resolve_time_window(params)
    if _should_query_usgs(db, start, end):
        try:
            payload = _query_events_page_from_usgs(params, start, end)
        except HTTPException as exc:
            if exc.status_code != 502:
                raise
            payload = _query_events_page_from_db(db, params, start, end)
        EVENT_QUERY_CACHE.put(cache_key, payload)
        return payload

    payload = _query_events_page_from_db(db, params, start, end)
    EVENT_QUERY_CACHE.put(cache_key, payload)
    return payload


def _query_events_page_from_db(
    db: Session,
    params: EventQueryParams,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    filters = [
        Earthquake.time >= start,
        Earthquake.time <= end,
        Earthquake.mag >= params.minMag,
    ]

    if params.maxMag is not None:
        filters.append(Earthquake.mag <= params.maxMag)
    if params.minDepth is not None:
        filters.append(Earthquake.depth_km >= params.minDepth)
    if params.maxDepth is not None:
        filters.append(Earthquake.depth_km <= params.maxDepth)

    if params.bbox:
        west, south, east, north = [float(part) for part in params.bbox.split(",")]
        filters.extend(
            [
                ST_X(Earthquake.geom) >= west,
                ST_X(Earthquake.geom) <= east,
                ST_Y(Earthquake.geom) >= south,
                ST_Y(Earthquake.geom) <= north,
            ]
        )
    else:
        if params.minLon is not None:
            filters.append(ST_X(Earthquake.geom) >= params.minLon)
        if params.maxLon is not None:
            filters.append(ST_X(Earthquake.geom) <= params.maxLon)
        if params.minLat is not None:
            filters.append(ST_Y(Earthquake.geom) >= params.minLat)
        if params.maxLat is not None:
            filters.append(ST_Y(Earthquake.geom) <= params.maxLat)

    stmt = (
        select(*EVENT_COLUMNS)
        .where(*filters)
        .order_by(Earthquake.time.desc())
        .offset(params.offset)
        .limit(params.limit)
    )
    count_stmt = select(func.count()).select_from(Earthquake).where(*filters)

    rows = db.execute(stmt).all()
    total = int(db.execute(count_stmt).scalar_one())
    payload = {
        "items": [serialize_event_row(row) for row in rows],
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
        "hasMore": params.offset + len(rows) < total,
    }
    return payload


def _resolve_time_window(params: EventQueryParams) -> tuple[datetime, datetime]:
    if params.start or params.end:
        end = params.end or datetime.now(tz=timezone.utc)
        start = params.start or end - timedelta(hours=params.hours or 24)
        return start, end
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(hours=params.hours or 24)
    return start, end


def _events_cache_key(params: EventQueryParams) -> str:
    return "|".join(
        [
            str(params.minMag),
            str(params.maxMag),
            str(params.hours),
            str(params.start),
            str(params.end),
            str(params.minDepth),
            str(params.maxDepth),
            str(params.bbox),
            str(params.minLon),
            str(params.maxLon),
            str(params.minLat),
            str(params.maxLat),
            str(params.limit),
            str(params.offset),
        ]
    )


def _should_query_usgs(db: Session, start: datetime, end: datetime) -> bool:
    bounds = db.execute(
        select(
            func.min(Earthquake.time).label("min_time"),
            func.max(Earthquake.time).label("max_time"),
        )
    ).one()
    db_min = bounds.min_time
    db_max = bounds.max_time
    if db_min is None or db_max is None:
        return True
    return start < db_min or end > db_max


def _query_events_page_from_usgs(
    params: EventQueryParams,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    query_params = _build_usgs_query_params(params, start, end)
    query_params["format"] = "geojson"
    query_params["orderby"] = "time"
    query_params["limit"] = str(min(params.limit + 1, 20000))
    query_params["offset"] = str(params.offset + 1)

    payload = _usgs_get(query_params, response_format="geojson")
    features = payload.get("features", [])
    has_more = len(features) > params.limit
    items = [_serialize_usgs_feature(feature) for feature in features[: params.limit]]
    total = params.offset + len(items) + (1 if has_more else 0)
    return {
        "items": items,
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
        "hasMore": has_more,
    }


def _build_usgs_query_params(
    params: EventQueryParams,
    start: datetime,
    end: datetime,
) -> dict[str, str]:
    query_params: dict[str, str] = {
        "starttime": start.isoformat(),
        "endtime": end.isoformat(),
        "minmagnitude": str(params.minMag),
    }
    if params.maxMag is not None:
        query_params["maxmagnitude"] = str(params.maxMag)
    if params.minDepth is not None:
        query_params["mindepth"] = str(params.minDepth)
    if params.maxDepth is not None:
        query_params["maxdepth"] = str(params.maxDepth)
    if params.bbox:
        west, south, east, north = [part.strip() for part in params.bbox.split(",")]
        query_params["minlongitude"] = west
        query_params["minlatitude"] = south
        query_params["maxlongitude"] = east
        query_params["maxlatitude"] = north
    else:
        if params.minLon is not None:
            query_params["minlongitude"] = str(params.minLon)
        if params.maxLon is not None:
            query_params["maxlongitude"] = str(params.maxLon)
        if params.minLat is not None:
            query_params["minlatitude"] = str(params.minLat)
        if params.maxLat is not None:
            query_params["maxlatitude"] = str(params.maxLat)
    return query_params


def _serialize_usgs_feature(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or [None, None, None]

    time_ms = properties.get("time")
    updated_ms = properties.get("updated")
    time_iso = _epoch_ms_to_iso(time_ms)
    updated_iso = _epoch_ms_to_iso(updated_ms)

    lon = coordinates[0] if len(coordinates) > 0 else None
    lat = coordinates[1] if len(coordinates) > 1 else None
    depth_km = coordinates[2] if len(coordinates) > 2 else None

    return {
        "id": feature.get("id"),
        "time": time_iso,
        "updated": updated_iso,
        "mag": properties.get("mag"),
        "place": properties.get("place"),
        "depth_km": depth_km,
        "lon": float(lon) if lon is not None else 0.0,
        "lat": float(lat) if lat is not None else 0.0,
        "magType": properties.get("magType"),
        "nst": properties.get("nst"),
        "gap": properties.get("gap"),
        "dmin": properties.get("dmin"),
        "rms": properties.get("rms"),
        "net": properties.get("net"),
        "type": properties.get("type"),
        "horizontalError": properties.get("horizontalError"),
        "depthError": properties.get("depthError"),
        "magError": properties.get("magError"),
        "magNst": properties.get("magNst"),
        "status": properties.get("status"),
        "locationSource": properties.get("locationSource"),
        "magSource": properties.get("magSource"),
    }


def _epoch_ms_to_iso(value: Any) -> str:
    if value is None:
        return datetime.now(tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()


def _usgs_get(params: dict[str, str], *, response_format: str) -> Any:
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(settings.usgs_base, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="USGS historical query is temporarily unavailable") from exc
    return response.json()

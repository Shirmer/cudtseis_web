'''
每 60 秒拉 USGS、写库、返回新增事件
'''

from datetime import datetime, timedelta, timezone
import requests
from sqlalchemy.orm import Session
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from .models import Earthquake
from .settings import settings

"""
每 60 秒拉 USGS、写库、返回新增事件
这里按 id 去重，满足“新增事件推送”。若你还想处理“事件属性更新”，可用 updated 字段判断并做 update。
"""

def _dt_ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

def fetch_usgs_geojson() -> dict:
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=1)

    params = {
        "format": "geojson",
        "starttime": start.isoformat(),
        "endtime": end.isoformat(),
        "minmagnitude": settings.min_magnitude,
        "orderby": "time",
    }
    r = requests.get(settings.usgs_base, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def upsert_and_get_new(db: Session, geojson: dict) -> list[dict]:
    new_items: list[dict] = []

    for f in geojson.get("features", []):
        eid = f.get("id")
        props = f.get("properties") or {}
        geom = f.get("geometry") or {}

        if not eid or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue

        lon, lat = float(coords[0]), float(coords[1])
        depth_km = float(coords[2]) if len(coords) >= 3 and coords[2] is not None else None

        mag = props.get("mag")
        tms = props.get("time")
        ums = props.get("updated")
        
        # 即使 mag 为 None 有时我们也可能想存，但这里保持您原有的校验逻辑
        if mag is None or tms is None or ums is None:
            continue

        mag = float(mag)
        t = _dt_ms_to_dt(int(tms))
        u = _dt_ms_to_dt(int(ums))
        place = props.get("place")

        # 检查是否存在
        exists = db.execute(select(Earthquake.id).where(Earthquake.id == eid)).first()
        if exists:
            # 如果需要更新现有数据（比如 updated 变了），可以在这里写逻辑
            continue
        
        # --- 关键修改：提取新字段 ---
        # 使用 .get() 方法，如果数据里没有这个字段，会自动设为 None，不会报错
        mag_type = props.get("magType")
        nst = props.get("nst")
        gap = props.get("gap")
        dmin = props.get("dmin")
        rms = props.get("rms")
        net = props.get("net")
        event_type = props.get("type") # 注意：python里 type 是关键字，所以我改名叫 event_type
        horizontal_error = props.get("horizontalError")
        depth_error = props.get("depthError")
        mag_error = props.get("magError")
        mag_nst = props.get("magNst")
        status = props.get("status")
        location_source = props.get("locationSource")
        mag_source = props.get("magSource")

        # --- 创建数据库对象 ---
        row = Earthquake(
            id=eid,
            time=t,
            updated=u,
            mag=mag,
            place=place,
            depth_km=depth_km,
            geom=from_shape(Point(lon, lat), srid=4326),
            
            # --- 填入新字段 ---
            mag_type=mag_type,
            nst=nst,
            gap=gap,
            dmin=dmin,
            rms=rms,
            net=net,
            type=event_type, # 对应模型的 type 字段
            horizontal_error=horizontal_error,
            depth_error=depth_error,
            mag_error=mag_error,
            mag_nst=mag_nst,
            status=status,
            location_source=location_source,
            mag_source=mag_source
        )
        db.add(row)

        # 构建返回给前端/WebSocket的数据包
        # 您可以根据需要把新字段也加进去
        new_items.append({
            "id": eid,
            "time": t.isoformat(),
            "updated": u.isoformat(),
            "mag": mag,
            "place": place,
            "depth_km": depth_km,
            "lon": lon,
            "lat": lat,
            "url": props.get("url"),
            "mag_type": mag_type, # 示例：如果前端立刻需要显示这个，就加在这里
            "type": event_type
        })

    if new_items:
        db.commit()
    return new_items
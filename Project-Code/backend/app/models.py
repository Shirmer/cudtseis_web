'''
PostGIS表
'''
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer
from geoalchemy2 import Geometry
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Earthquake(Base):
    __tablename__ = "earthquakes"

    # --- 核心字段 ---
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    mag: Mapped[Optional[float]] = mapped_column(Float, index=True, nullable=True)
    place: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    depth_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), index=True)

    mag_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nst: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dmin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    horizontal_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    depth_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mag_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mag_nst: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mag_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

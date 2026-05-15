'''
PostGIS表
'''
from __future__ import annotations

from typing import Any, Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint, func
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


class GeoDocument(Base):
    __tablename__ = "geo_documents"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    authors_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    doi: Mapped[str] = mapped_column(String(200), index=True, default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    file_name: Mapped[str] = mapped_column(String(500), default="")
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    parser: Mapped[str] = mapped_column(String(80), default="mvp-text")
    parser_version: Mapped[str] = mapped_column(String(80), default="mvp-text-v1")
    status: Mapped[str] = mapped_column(String(40), default="indexed")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    unit_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeUnit(Base):
    __tablename__ = "knowledge_units"
    __table_args__ = (
        UniqueConstraint("document_id", "unit_index", "content_type", name="uq_knowledge_unit_doc_index_type"),
    )

    id: Mapped[str] = mapped_column(String(220), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(160), index=True)
    paper_id: Mapped[str] = mapped_column(String(160), index=True)
    unit_index: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(40), index=True, default="text")
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[str] = mapped_column(String(300), default="")
    bbox_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    regions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    faults_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    topics_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    geo_entities_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    modality_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    citation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding_backend: Mapped[str] = mapped_column(String(80), default="raganything")
    index_version: Mapped[str] = mapped_column(String(80), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentKnowledgeCard(Base):
    __tablename__ = "document_knowledge_cards"

    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(160), index=True)
    paper_id: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    schema_version: Mapped[str] = mapped_column(String(80), default="knowledge-card-v1")
    card_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    card_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentImportJob(Base):
    __tablename__ = "document_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    directory_path: Mapped[str] = mapped_column(String(1000), default="")
    recursive: Mapped[bool] = mapped_column(default=False)
    force: Mapped[bool] = mapped_column(default=False)
    limit: Mapped[int] = mapped_column(Integer, default=100)
    extensions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), index=True, default="queued")
    total: Mapped[int] = mapped_column(Integer, default=0)
    queued: Mapped[int] = mapped_column(Integer, default=0)
    running: Mapped[int] = mapped_column(Integer, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentImportItem(Base):
    __tablename__ = "document_import_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(40), index=True, default="queued")
    document_id: Mapped[str] = mapped_column(String(160), default="")
    paper_id: Mapped[str] = mapped_column(String(160), default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    units: Mapped[int] = mapped_column(Integer, default=0)
    multimodal_units: Mapped[int] = mapped_column(Integer, default=0)
    storage_uri: Mapped[str] = mapped_column(String(1000), default="")
    embedding_backend: Mapped[str] = mapped_column(String(80), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

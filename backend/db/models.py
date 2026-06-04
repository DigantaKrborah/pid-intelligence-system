import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, BigInteger, Float, Boolean,
    DateTime, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.db.database import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents: Mapped[list["PIDDocument"]] = relationship(back_populates="unit", cascade="all, delete-orphan")
    equipment_tags: Mapped[list["EquipmentTag"]] = relationship(back_populates="unit", cascade="all, delete-orphan")


class PIDDocument(Base):
    __tablename__ = "pid_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(500))
    file_path: Mapped[str | None] = mapped_column(String(1000))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    page_count: Mapped[int | None] = mapped_column(Integer)
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text)
    tags_extracted: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    unit: Mapped["Unit"] = relationship(back_populates="documents")
    equipment_tags: Mapped[list["EquipmentTag"]] = relationship(back_populates="document")


class EquipmentTag(Base):
    __tablename__ = "equipment_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pid_documents.id", ondelete="SET NULL"))
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    coordinates: Mapped[dict | None] = mapped_column(JSONB)
    raw_attributes: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    unit: Mapped["Unit"] = relationship(back_populates="equipment_tags")
    document: Mapped["PIDDocument"] = relationship(back_populates="equipment_tags")

    __table_args__ = (
        UniqueConstraint("unit_id", "tag", name="uq_unit_tag"),
        Index("ix_equipment_tags_unit_id", "unit_id"),
        Index("ix_equipment_tags_tag", "tag"),
        Index("ix_equipment_tags_tag_type", "tag_type"),
    )


class TagConnection(Base):
    __tablename__ = "tag_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment_tags.id", ondelete="CASCADE"), nullable=False)
    target_tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment_tags.id", ondelete="CASCADE"), nullable=False)
    connection_type: Mapped[str | None] = mapped_column(String(50))
    line_number: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pid | sop
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(20))   # critical | high | medium | low
    related_tags: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EngineeringDocument(Base):
    __tablename__ = "engineering_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="SET NULL"))
    doc_type: Mapped[str | None] = mapped_column(String(50))   # SOP | manual | procedure | datasheet
    title: Mapped[str | None] = mapped_column(String(500))
    filename: Mapped[str | None] = mapped_column(String(500))
    file_path: Mapped[str | None] = mapped_column(String(1000))
    page_count: Mapped[int | None] = mapped_column(Integer)
    indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    unit: Mapped["Unit"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict | None] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

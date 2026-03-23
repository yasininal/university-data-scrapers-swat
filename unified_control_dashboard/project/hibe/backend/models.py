"""SQLAlchemy ORM models for the Grant Dashboard"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from database import Base


class Source(Base):
    """Grant source/portal"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    url = Column(String(500), nullable=False)
    scraper_type = Column(String(50), nullable=False)  # 'api' or 'html'
    active = Column(Boolean, default=True, index=True)
    last_scraped = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationship
    calls = relationship("GrantCall", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name}, active={self.active})>"


class GrantCall(Base):
    """Grant call / funding opportunity"""
    __tablename__ = "grant_calls"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)

    # Core identifying fields
    original_id = Column(String(255), nullable=True, index=True)  # ID from source portal
    program_name = Column(String(500), nullable=True, index=True)
    call_title = Column(String(1000), nullable=False, index=True)
    url = Column(String(500), unique=True, nullable=False, index=True)

    # Metadata
    deadline = Column(DateTime(timezone=True), nullable=True, index=True)
    budget_amount = Column(Float, nullable=True)
    budget_currency = Column(String(10), nullable=True)  # EUR, TRY, USD, etc.
    sector = Column(String(255), nullable=True, index=True)

    # Detailed text
    description = Column(Text, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)

    # Status tracking
    status = Column(String(50), default="active", index=True)  # active, expired, archived
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    source = relationship("Source", back_populates="calls")

    # Indexes
    __table_args__ = (
        Index("idx_source_status", "source_id", "status"),
        Index("idx_deadline_status", "deadline", "status"),
    )

    def __repr__(self) -> str:
        return f"<GrantCall(id={self.id}, title={self.call_title[:50]}...)>"

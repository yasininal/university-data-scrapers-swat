"""Pydantic schemas for request/response validation"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class SourceBase(BaseModel):
    """Base source schema"""
    name: str
    url: str
    scraper_type: str = Field(..., description="'api' or 'html'")
    active: bool = True


class SourceCreate(SourceBase):
    """Schema for creating a source"""
    pass


class SourceResponse(SourceBase):
    """Schema for source response"""
    id: int
    last_scraped: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GrantCallBase(BaseModel):
    """Base grant call schema"""
    source_name: Optional[str] = None
    original_id: Optional[str] = None
    program_name: Optional[str] = None
    call_title: str
    url: str
    deadline: Optional[datetime] = None
    budget_amount: Optional[float] = None
    budget_currency: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[str] = None

    @field_validator("call_title", "url")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Field cannot be empty")
        return str(v).strip()

    @field_validator("budget_currency")
    @classmethod
    def normalize_currency(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = str(v).strip().upper()
        # Normalize common Turkish currency usages
        if v in ["TL", "TRY", "₺"]:
            return "TRY"
        if v in ["EUR", "€", "EURO"]:
            return "EUR"
        if v in ["USD", "$"]:
            return "USD"
        if v in ["GBP", "£"]:
            return "GBP"
        return v


class GrantCallCreate(GrantCallBase):
    """Schema for creating a grant call"""
    source_id: Optional[int] = None


class GrantCallUpdate(BaseModel):
    """Schema for updating a grant call"""
    call_title: Optional[str] = None
    deadline: Optional[datetime] = None
    budget_amount: Optional[float] = None
    sector: Optional[str] = None
    status: Optional[str] = None


class GrantCallResponse(GrantCallBase):
    """Schema for grant call response"""
    id: int
    source_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_opportunities: int
    total_sources: int
    active_opportunities: int
    expiring_soon: int  # Within 7 days
    by_source: dict  # {source_name: count}
    by_sector: dict  # {sector_name: count}
    total_budget: dict  # {currency: amount}
    last_update: Optional[datetime] = None


class ScraperResult(BaseModel):
    """Result from a scraper run"""
    source_name: str
    status: str  # 'success', 'error', 'partial'
    records_found: int
    records_created: int
    records_updated: int
    error_message: Optional[str] = None
    execution_time: float  # seconds
    timestamp: datetime

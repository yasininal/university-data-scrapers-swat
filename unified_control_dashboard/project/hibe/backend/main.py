"""FastAPI application for Grant Dashboard"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from config import CORS_ORIGINS, API_V1_PREFIX, API_TITLE
from database import get_db, init_db
from models import Source, GrantCall
from schemas import (
    GrantCallResponse,
    SourceResponse,
    DashboardStats,
    GrantCallCreate,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(title=API_TITLE)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/")
def read_root():
    """Root endpoint health check"""
    return {
        "status": "ok",
        "message": "Grant Monitoring API is running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# Opportunities Endpoints
# ============================================================================

@app.get(f"{API_V1_PREFIX}/opportunities", response_model=List[GrantCallResponse])
def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    source: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    deadline_min: Optional[str] = Query(None),
    deadline_max: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    List all active grant opportunities with optional filtering.

    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Number of records to return (max 500)
    - source: Filter by source name
    - sector: Filter by sector
    - search: Search in call_title and description
    - status: Filter by status (default: 'active')
    - deadline_min: Filter deadlines from this date (ISO format)
    - deadline_max: Filter deadlines until this date (ISO format)
    """
    query = db.query(GrantCall)

    # Apply filters
    if status:
        query = query.filter(GrantCall.status == status)
    else:
        query = query.filter(GrantCall.status == "active")

    if source:
        query = query.filter(GrantCall.source.has(Source.name == source))

    if sector:
        query = query.filter(GrantCall.sector == sector)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (GrantCall.call_title.ilike(search_term)) |
            (GrantCall.description.ilike(search_term))
        )

    if deadline_min:
        try:
            min_date = datetime.fromisoformat(deadline_min)
            query = query.filter(GrantCall.deadline >= min_date)
        except ValueError:
            pass

    if deadline_max:
        try:
            max_date = datetime.fromisoformat(deadline_max)
            query = query.filter(GrantCall.deadline <= max_date)
        except ValueError:
            pass

    # Sort by deadline ascending (soonest first)
    query = query.order_by(GrantCall.deadline.asc())

    # Pagination
    total = query.count()
    opportunities = query.offset(skip).limit(limit).all()

    # Log response with source information for debugging
    for opp in opportunities:
        if opp.source:
            opp.source_name = opp.source.name

    return opportunities


@app.get(f"{API_V1_PREFIX}/opportunities/{{opportunity_id}}", response_model=GrantCallResponse)
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """Get details for a specific grant opportunity"""
    opportunity = db.query(GrantCall).filter(GrantCall.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opportunity.source:
        opportunity.source_name = opportunity.source.name

    return opportunity


# ============================================================================
# Sources Endpoints
# ============================================================================

@app.get(f"{API_V1_PREFIX}/sources", response_model=List[SourceResponse])
def list_sources(db: Session = Depends(get_db)):
    """List all sources and their status"""
    sources = db.query(Source).all()
    return sources


@app.get(f"{API_V1_PREFIX}/sources/{{source_id}}", response_model=SourceResponse)
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Get details for a specific source"""
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return source


# ============================================================================
# Statistics Endpoints
# ============================================================================

@app.get(f"{API_V1_PREFIX}/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    now = datetime.utcnow()
    week_from_now = now + timedelta(days=7)

    # Count all opportunities
    total_opportunities = db.query(GrantCall).filter(
        GrantCall.status == "active"
    ).count()

    # Count active opportunities (deadline in future)
    active_opportunities = db.query(GrantCall).filter(
        and_(
            GrantCall.status == "active",
            GrantCall.deadline > now
        )
    ).count()

    # Count expiring soon (within 7 days)
    expiring_soon = db.query(GrantCall).filter(
        and_(
            GrantCall.status == "active",
            GrantCall.deadline.between(now, week_from_now)
        )
    ).count()

    # Count by source
    by_source_data = db.query(
        Source.name,
        func.count(GrantCall.id).label("count")
    ).join(GrantCall).filter(
        GrantCall.status == "active"
    ).group_by(Source.name).all()

    by_source = {name: count for name, count in by_source_data}

    # Count by sector
    by_sector_data = db.query(
        GrantCall.sector,
        func.count(GrantCall.id).label("count")
    ).filter(
        GrantCall.status == "active",
        GrantCall.sector.isnot(None)
    ).group_by(GrantCall.sector).all()

    by_sector = {sector or "Genel": count for sector, count in by_sector_data}

    # Sum budget by currency
    budget_data = db.query(
        GrantCall.budget_currency,
        func.sum(GrantCall.budget_amount).label("total")
    ).filter(
        GrantCall.status == "active",
        GrantCall.budget_amount.isnot(None)
    ).group_by(GrantCall.budget_currency).all()

    total_budget = {
        currency or "Unknown": total or 0
        for currency, total in budget_data
    }

    # Get last update time
    last_source = db.query(Source.last_scraped).order_by(
        desc(Source.last_scraped)
    ).first()
    last_update = last_source[0] if last_source and last_source[0] else None

    # Count all sources
    total_sources = db.query(Source).filter(Source.active == True).count()

    return DashboardStats(
        total_opportunities=total_opportunities,
        total_sources=total_sources,
        active_opportunities=active_opportunities,
        expiring_soon=expiring_soon,
        by_source=by_source,
        by_sector=by_sector,
        total_budget=total_budget,
        last_update=last_update,
    )


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.post(f"{API_V1_PREFIX}/scrape")
def trigger_scrape(db: Session = Depends(get_db)):
    """
    Trigger manual scraping of all sources.

    This endpoint runs the scrapers and updates the database.
    Use run_scrapers.py for a proper standalone implementation.
    """
    from scrapers import EUFundingScraper, EUAffairsScraper, YatirimaDestekScraper

    results = []

    for scraper_class, source_name in [
        (EUFundingScraper, "EU Funding & Tenders Portal"),
        (EUAffairsScraper, "AB Bakanlığı Güncel Hibeler"),
        (YatirimaDestekScraper, "Yatırıma Destek Portalı"),
    ]:
        try:
            scraper = scraper_class()
            grants = scraper.get_data()

            # Get or create source
            source = db.query(Source).filter(Source.name == source_name).first()
            if not source:
                source = Source(
                    name=source_name,
                    url=scraper.source_url,
                    scraper_type="api" if "Funding" in source_name else "html",
                )
                db.add(source)
                db.commit()

            # Add or update grants
            created = 0
            updated = 0

            for grant_data in grants:
                existing = db.query(GrantCall).filter(
                    GrantCall.url == grant_data["url"]
                ).first()

                if existing:
                    # Update existing
                    for key, value in grant_data.items():
                        if value is not None and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create new
                    new_grant = GrantCall(
                        source_id=source.id,
                        **grant_data,
                        status="active",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(new_grant)
                    created += 1

            db.commit()

            # Update source last_scraped time
            source.last_scraped = datetime.utcnow()
            db.commit()

            results.append({
                "source": source_name,
                "status": "success",
                "grants_found": len(grants),
                "created": created,
                "updated": updated,
            })

            logger.info(f"Scraped {source_name}: {created} created, {updated} updated")

        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            results.append({
                "source": source_name,
                "status": "error",
                "error": str(e),
            })

    return {
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat(),
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

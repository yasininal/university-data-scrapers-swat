"""
Initialize database with sample sources.
Run this once to set up the database structure.

Usage:
    python init_db.py
"""

import logging
from datetime import datetime
from database import SessionLocal, init_db
from models import Source, GrantCall


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database tables and create sample sources"""
    logger.info("Initializing database...")

    # Create tables
    init_db()
    logger.info("✓ Database tables created")

    # Create session
    db = SessionLocal()

    try:
        # Check if sources already exist
        existing_sources = db.query(Source).count()

        if existing_sources > 0:
            logger.info(f"Database already contains {existing_sources} sources. Skipping initialization.")
            return

        # Create default sources
        sources = [
            Source(
                name="EU Funding & Tenders Portal",
                url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
                scraper_type="api",
                active=True,
            ),
            Source(
                name="AB Bakanlığı Güncel Hibeler",
                url="https://www.ab.gov.tr/guncel-hibeler_4.html",
                scraper_type="html",
                active=True,
            ),
            Source(
                name="Yatırıma Destek Portalı",
                url="https://www.yatirimadestek.gov.tr/destek-arama",
                scraper_type="html",
                active=True,
            ),
        ]

        for source in sources:
            db.add(source)
            logger.info(f"✓ Created source: {source.name}")

        db.commit()
        logger.info("✓ Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()

"""
Standalone script to run all scrapers and update the database.

Usage:
    python run_scrapers.py              # Run all scrapers once
    python run_scrapers.py --schedule   # Run on a schedule (daily)
    python run_scrapers.py --source <name>  # Run specific source
"""

import logging
import argparse
import sys
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Source, GrantCall
from scrapers import EUFundingScraper, EUAffairsScraper, YatirimaDestekScraper


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ScraperRunner:
    """Manages running and tracking scrapers"""

    def __init__(self):
        init_db()
        self.db = SessionLocal()
        self.scrapers = {
            "eu_funding": EUFundingScraper(),
            "eu_affairs": EUAffairsScraper(),
            "yatirima_destek": YatirimaDestekScraper(),
        }

    def get_source(self, scraper_name: str, scraper) -> Source:
        """Get or create a source in the database"""
        source = self.db.query(Source).filter(
            Source.name == scraper.source_name
        ).first()

        if not source:
            source = Source(
                name=scraper.source_name,
                url=scraper.source_url,
                scraper_type="api" if scraper_name == "eu_funding" else "html",
                active=True,
            )
            self.db.add(source)
            self.db.commit()
            logger.info(f"Created new source: {source.name}")
        else:
            logger.info(f"Using existing source: {source.name}")

        return source

    def run_scraper(self, scraper_name: str, scraper) -> dict:
        """
        Run a single scraper and update database.
        Each grant is committed individually so one bad record
        never aborts the whole batch and never poisons the session.
        """
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info(f"Starting scraper: {scraper_name}")

        # Always start with a clean session state
        try:
            self.db.rollback()
        except Exception:
            pass

        try:
            grants = scraper.get_data()
            logger.info(f"Scraper returned {len(grants)} grants")

            source = self.get_source(scraper_name, scraper)

            created = 0
            updated = 0
            skipped = 0
            seen_urls: set = set()          # deduplicate within this batch

            for grant_data in grants:
                url = grant_data.get("url", "").strip()
                if not url or url in seen_urls:
                    skipped += 1
                    continue
                seen_urls.add(url)

                try:
                    existing = self.db.query(GrantCall).filter(
                        GrantCall.url == url
                    ).first()

                    if existing:
                        for key, value in grant_data.items():
                            if value is not None and hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        updated += 1
                    else:
                        new_grant = GrantCall(
                            source_id=source.id,
                            **grant_data,
                            status="active",
                            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        )
                        self.db.add(new_grant)
                        created += 1

                    # Commit each record individually — one failure won't kill the batch
                    self.db.commit()

                except Exception as e:
                    self.db.rollback()          # reset session before next record
                    logger.warning(f"Skipped grant '{url}': {e}")
                    skipped += 1
                    continue

            source.last_scraped = datetime.now(timezone.utc).replace(tzinfo=None)
            self.db.commit()

            execution_time = (datetime.now(timezone.utc).replace(tzinfo=None) - start_time).total_seconds()

            result = {
                "source_name": scraper.source_name,
                "status": "success",
                "records_found": len(grants),
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "execution_time": execution_time,
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }

            logger.info(
                f"Scraper {scraper_name} completed: "
                f"{created} created, {updated} updated, {skipped} skipped "
                f"({execution_time:.2f}s)"
            )
            return result

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in scraper {scraper_name}: {e}", exc_info=True)
            return {
                "source_name": scraper.source_name,
                "status": "error",
                "error": str(e),
                "execution_time": (datetime.now(timezone.utc).replace(tzinfo=None) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }

    def run_all(self) -> List[dict]:
        """Run all scrapers"""
        logger.info("=" * 60)
        logger.info("Starting scraper run for all sources")
        logger.info("=" * 60)

        results = []

        for scraper_name, scraper in self.scrapers.items():
            result = self.run_scraper(scraper_name, scraper)
            results.append(result)

        logger.info("=" * 60)
        logger.info("Scraper run completed")
        logger.info("=" * 60)

        self._print_summary(results)
        return results

    def run_single(self, source_name: str) -> dict:
        """Run a specific scraper"""
        logger.info(f"Running scraper for: {source_name}")

        scraper_name = None
        scraper = None

        # Map source name to scraper
        source_mapping = {
            "eu_funding": ("eu_funding", EUFundingScraper()),
            "eu_affairs": ("eu_affairs", EUAffairsScraper()),
            "yatirima": ("yatirima_destek", YatirimaDestekScraper()),
        }

        for key, (name, s) in source_mapping.items():
            if key in source_name.lower():
                scraper_name = name
                scraper = s
                break

        if not scraper:
            logger.error(f"Unknown source: {source_name}")
            return {"status": "error", "error": f"Unknown source: {source_name}"}

        result = self.run_scraper(scraper_name, scraper)
        self._print_summary([result])
        return result

    def _print_summary(self, results: List[dict]):
        """Print summary of scraper results"""
        logger.info("\nSummary:")
        logger.info("-" * 60)

        total_found = 0
        total_created = 0
        total_updated = 0

        for result in results:
            source = result.get("source_name", "Unknown")
            status = result.get("status", "unknown")

            if status == "success":
                found = result.get("records_found", 0)
                created = result.get("created", 0)
                updated = result.get("updated", 0)
                exec_time = result.get("execution_time", 0)

                total_found += found
                total_created += created
                total_updated += updated

                logger.info(
                    f"  {source:<30} | Found: {found:>3} | "
                    f"Created: {created:>3} | Updated: {updated:>3} | "
                    f"Time: {exec_time:.2f}s"
                )
            else:
                error = result.get("error", "Unknown error")
                logger.info(f"  {source:<30} | ERROR: {error}")

        logger.info("-" * 60)
        logger.info(
            f"Total: Found {total_found} | Created {total_created} | Updated {total_updated}"
        )

    def close(self):
        """Close database session"""
        self.db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Grant Dashboard Scraper Runner"
    )
    parser.add_argument(
        "--source",
        help="Run specific source (eu_funding, eu_affairs, yatirima)",
        default=None,
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on daily schedule (requires APScheduler)",
    )

    args = parser.parse_args()

    runner = ScraperRunner()

    try:
        if args.schedule:
            # Run on schedule using APScheduler
            try:
                from apscheduler.schedulers.blocking import BlockingScheduler
            except ImportError:
                logger.error("APScheduler not installed. Install with: pip install apscheduler")
                sys.exit(1)

            scheduler = BlockingScheduler()

            # Run daily at 2 AM UTC (5 AM CET, 6 AM EET)
            scheduler.add_job(
                runner.run_all,
                'cron',
                hour=2,
                minute=0,
                id='scraper_job'
            )

            logger.info("Scheduler started. Running scrapers daily at 2:00 AM UTC")
            logger.info("Press Ctrl+C to stop")

            try:
                scheduler.start()
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                scheduler.shutdown()

        elif args.source:
            # Run single scraper
            runner.run_single(args.source)

        else:
            # Run all scrapers once
            runner.run_all()

    finally:
        runner.close()


if __name__ == "__main__":
    main()

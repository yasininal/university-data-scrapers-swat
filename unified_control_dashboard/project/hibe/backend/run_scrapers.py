"""
Standalone script to run all scrapers and update the database.

Usage:
    python run_scrapers.py              # Run all scrapers once
    python run_scrapers.py --schedule   # Run on a schedule (daily)
    python run_scrapers.py --source <name>  # Run specific source

E-posta bildirimi icin .env dosyasina ekle:
    NOTIFY_EMAIL_ENABLED=true
    NOTIFY_SMTP_HOST=smtp.gmail.com
    NOTIFY_SMTP_PORT=587
    NOTIFY_SMTP_USER=kullanici@gmail.com
    NOTIFY_SMTP_PASSWORD=uygulama_sifresi
    NOTIFY_TO=hedef@ornek.com
"""

import logging
import argparse
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Source, GrantCall
from scrapers import EUFundingScraper, EUAffairsScraper, YatirimaDestekScraper
import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# E-posta yardımcıları
# ---------------------------------------------------------------------------

def _build_summary_html(results: List[dict]) -> str:
    rows = ""
    for r in results:
        status = r.get("status", "unknown")
        color = "#2ecc71" if status == "success" else "#e74c3c"
        if status == "success":
            detail = (
                f"Bulunan: {r.get('records_found', 0)} | "
                f"Yeni: {r.get('created', 0)} | "
                f"Guncellenen: {r.get('updated', 0)} | "
                f"Sure: {r.get('execution_time', 0):.1f}s"
            )
        else:
            detail = f"HATA: {r.get('error', 'Bilinmeyen hata')}"
        rows += (
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{r.get('source_name','?')}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee;color:{color};font-weight:bold'>{status.upper()}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{detail}</td>"
            f"</tr>"
        )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <html><body style='font-family:Arial,sans-serif;color:#333'>
      <h2 style='color:#2c3e50'>Grant Dashboard — Scraper Ozeti</h2>
      <p style='color:#666'>{ts}</p>
      <table style='border-collapse:collapse;width:100%;max-width:700px'>
        <thead>
          <tr style='background:#f5f5f5'>
            <th style='padding:8px 12px;text-align:left'>Kaynak</th>
            <th style='padding:8px 12px;text-align:left'>Durum</th>
            <th style='padding:8px 12px;text-align:left'>Detay</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </body></html>
    """


def _build_error_html(scraper_name: str, error: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <html><body style='font-family:Arial,sans-serif;color:#333'>
      <h2 style='color:#e74c3c'>Grant Dashboard — Scraper Hatasi</h2>
      <p style='color:#666'>{ts}</p>
      <p><strong>Kaynak:</strong> {scraper_name}</p>
      <p><strong>Hata:</strong></p>
      <pre style='background:#f9f9f9;padding:12px;border-left:4px solid #e74c3c'>{error}</pre>
    </body></html>
    """


def send_email(subject: str, html_body: str) -> bool:
    """SMTP ile e-posta gonder. Hata durumunda False donerve loglara yazar."""
    if not config.NOTIFY_EMAIL_ENABLED:
        return False

    missing = [v for v in ["NOTIFY_SMTP_HOST", "NOTIFY_SMTP_USER", "NOTIFY_SMTP_PASSWORD", "NOTIFY_TO"]
               if not getattr(config, v, "")]
    if missing:
        logger.warning(f"E-posta bildirimi devre disi: eksik ayarlar: {', '.join(missing)}")
        return False

    recipients = [r.strip() for r in config.NOTIFY_TO.split(",") if r.strip()]
    if not recipients:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.NOTIFY_FROM or config.NOTIFY_SMTP_USER
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(config.NOTIFY_SMTP_HOST, config.NOTIFY_SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(config.NOTIFY_SMTP_USER, config.NOTIFY_SMTP_PASSWORD)
            server.sendmail(msg["From"], recipients, msg.as_string())

        logger.info(f"Bildirim e-postasi gonderildi -> {', '.join(recipients)}")
        return True
    except Exception as exc:
        logger.error(f"E-posta gonderilemedi: {exc}")
        return False


# ---------------------------------------------------------------------------
# ScraperRunner
# ---------------------------------------------------------------------------

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
        Hata durumunda e-posta bildirimi gonderir.
        """
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info(f"Starting scraper: {scraper_name}")

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
            seen_urls: set = set()

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

                    self.db.commit()

                except Exception as e:
                    self.db.rollback()
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
            error_msg = str(e)
            logger.error(f"Error in scraper {scraper_name}: {error_msg}", exc_info=True)

            # Hata bildirimi gonder
            send_email(
                subject=f"[Grant Dashboard] Scraper Hatasi: {scraper_name}",
                html_body=_build_error_html(scraper_name, error_msg),
            )

            return {
                "source_name": scraper.source_name,
                "status": "error",
                "error": error_msg,
                "execution_time": (
                    datetime.now(timezone.utc).replace(tzinfo=None) - start_time
                ).total_seconds(),
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }

    def run_all(self) -> List[dict]:
        """Run all scrapers and send summary notification."""
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

        # Ozet bildirim gonder
        total_new = sum(r.get("created", 0) for r in results)
        errors = [r for r in results if r.get("status") == "error"]
        if errors:
            subject = f"[Grant Dashboard] {len(errors)} kaynak hata verdi — {total_new} yeni hibe"
        elif total_new > 0:
            subject = f"[Grant Dashboard] {total_new} yeni hibe bulundu"
        else:
            subject = "[Grant Dashboard] Scraper calisti — yeni hibe yok"
        send_email(subject=subject, html_body=_build_summary_html(results))

        return results

    def run_single(self, source_name: str) -> dict:
        """Run a specific scraper"""
        logger.info(f"Running scraper for: {source_name}")

        scraper_name = None
        scraper = None

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
    parser = argparse.ArgumentParser(description="Grant Dashboard Scraper Runner")
    parser.add_argument("--source", help="Run specific source (eu_funding, eu_affairs, yatirima)", default=None)
    parser.add_argument("--schedule", action="store_true", help="Run on daily schedule (requires APScheduler)")

    args = parser.parse_args()
    runner = ScraperRunner()

    try:
        if args.schedule:
            try:
                from apscheduler.schedulers.blocking import BlockingScheduler
            except ImportError:
                logger.error("APScheduler not installed. Install with: pip install apscheduler")
                sys.exit(1)

            scheduler = BlockingScheduler()
            scheduler.add_job(runner.run_all, 'cron', hour=2, minute=0, id='scraper_job')

            logger.info("Scheduler started. Running scrapers daily at 2:00 AM UTC")
            logger.info("Press Ctrl+C to stop")

            try:
                scheduler.start()
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                scheduler.shutdown()

        elif args.source:
            runner.run_single(args.source)
        else:
            runner.run_all()

    finally:
        runner.close()


if __name__ == "__main__":
    main()

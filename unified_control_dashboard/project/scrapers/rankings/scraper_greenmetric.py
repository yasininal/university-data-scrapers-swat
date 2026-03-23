"""
UI GreenMetric World University Rankings 2025 - Scraper
Extracts ranking data for Turkish universities from greenmetric.ui.ac.id
Uses Playwright for dynamic JavaScript-rendered content (DataTables).
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd

# ─── Configuration ───────────────────────────────────────────────────────────
URL = "https://uigreenmetric.com/rankings/university/overall-rankings-2025"
COUNTRY_FILTER_VALUE = "Turkiye"
ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_FILE = str(OUTPUT_DIR / "greenmetric_turkey_2025.xlsx")
JSON_BACKUP = str(OUTPUT_DIR / "greenmetric_turkey_2025.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


import random
import time

TABLE_SELECTORS = [
    "#overallTable",
    "table#overallTable",
    "#tableranking",
    "table#tableranking",
    "table.dataTable",
    "table.table",
]

COUNTRY_FILTER_SELECTORS = [
    "#countryFilter",
    "select[name='countryFilter']",
    "select[id*='country']",
]

LENGTH_SELECTORS = [
    "#entriesPerPage",
    "select#entriesPerPage",
    "select.filter-select--small",
    ".table-controls select",
    "select[name='tableranking_length']",
    "div.dataTables_length select",
]

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]
    return random.choice(user_agents)


def _wait_for_any_selector(page, selectors: list[str], timeout_per_selector: int = 12000) -> str | None:
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=timeout_per_selector)
            return selector
        except PlaywrightTimeoutError:
            continue
    return None


def _apply_country_filter(page, country_text: str) -> bool:
    for selector in COUNTRY_FILTER_SELECTORS:
        matched = page.evaluate(
            """
            ({selector, countryText}) => {
                const filter = document.querySelector(selector);
                if (!filter) return false;
                const options = Array.from(filter.options || []);
                const target = options.find((o) =>
                    (o.textContent || '').toLowerCase().includes(countryText.toLowerCase())
                );
                if (!target) return false;
                filter.value = target.value;
                filter.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
            """,
            {"selector": selector, "countryText": country_text},
        )
        if matched:
            return True
    return False


def _expand_table_length(page, desired: str = "500") -> bool:
    for selector in LENGTH_SELECTORS:
        updated = page.evaluate(
            """
            ({selector, desired}) => {
                const lengthSelect = document.querySelector(selector);
                if (!lengthSelect) return false;
                const exists = Array.from(lengthSelect.options || []).some((o) => o.value === desired);
                if (!exists) {
                    const opt = document.createElement('option');
                    opt.value = desired;
                    opt.textContent = desired;
                    lengthSelect.appendChild(opt);
                }
                lengthSelect.value = desired;
                lengthSelect.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
            """,
            {"selector": selector, "desired": desired},
        )
        if updated:
            return True
    return False


def _extract_rows(page, table_selector: str):
    return page.evaluate(
        """
        ({tableSelector}) => {
            const table = document.querySelector(tableSelector);
            if (!table) return [];

            const headerCells = Array.from(table.querySelectorAll('thead th'));
            const headers = headerCells.map((th) => (th.textContent || '').trim().toLowerCase());
            const idx = (candidates, fallback) => {
                for (const c of candidates) {
                    const found = headers.findIndex((h) => h.includes(c));
                    if (found >= 0) return found;
                }
                return fallback;
            };

            const worldRankIdx = idx(['world rank', 'world'], 0);
            const countryRankIdx = idx(['country rank', 'country'], 1);
            const universityIdx = idx(['university'], 2);
            const totalScoreIdx = idx(['total score', 'overall'], 3);
            const siIdx = idx(['setting', 'infrastructure', 'si'], 4);
            const ecIdx = idx(['energy', 'climate', 'ec'], 5);
            const wsIdx = idx(['waste', 'ws'], 6);
            const wrIdx = idx(['water', 'wr'], 7);
            const trIdx = idx(['transportation', 'tr'], 8);
            const edIdx = idx(['education', 'research', 'ed'], 9);

            const rows = Array.from(table.querySelectorAll('tbody tr'));
            return rows.map((row) => {
                const cells = Array.from(row.querySelectorAll('td'));
                if (cells.length < 3) return null;

                const getCellText = (index) => {
                    const cell = cells[index];
                    if (!cell) return '';
                    return (cell.textContent || '').trim();
                };

                const uniCell = cells[universityIdx] || cells[2];
                let uniName = '';
                if (uniCell) {
                    const link = uniCell.querySelector('a');
                    uniName = link ? (link.textContent || '').trim() : (uniCell.textContent || '').trim().split('\\n')[0].trim();
                }

                if (!uniName) return null;

                const parseIntOrText = (value) => {
                    const v = (value || '').trim();
                    const p = parseInt(v, 10);
                    return Number.isNaN(p) ? v : p;
                };

                const parseFloatOrZero = (value) => {
                    const normalized = (value || '').replace(',', '.').trim();
                    const p = parseFloat(normalized);
                    return Number.isNaN(p) ? 0 : p;
                };

                return {
                    world_rank: parseIntOrText(getCellText(worldRankIdx)),
                    country_rank: parseIntOrText(getCellText(countryRankIdx)),
                    university: uniName,
                    country: (row.getAttribute('data-country') || '').trim(),
                    total_score: parseFloatOrZero(getCellText(totalScoreIdx)),
                    si_score: parseFloatOrZero(getCellText(siIdx)),
                    ec_score: parseFloatOrZero(getCellText(ecIdx)),
                    ws_score: parseFloatOrZero(getCellText(wsIdx)),
                    wr_score: parseFloatOrZero(getCellText(wrIdx)),
                    tr_score: parseFloatOrZero(getCellText(trIdx)),
                    ed_score: parseFloatOrZero(getCellText(edIdx)),
                };
            }).filter(Boolean);
        }
        """,
        {"tableSelector": table_selector},
    )

def scrape_greenmetric() -> pd.DataFrame:
    """
    Launch headless browser, navigate to GreenMetric rankings,
    filter by Turkey, and extract all university data.
    """
    logger.info("Starting GreenMetric scraper...")
    logger.info(f"Target URL: {URL}")

    with sync_playwright() as p:
        # Daha gerçekçi görünmesi için tarayıcı başlıklarını ekliyoruz
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",  # Bot algılamayı kapat
                "--lang=tr-TR,tr,en-US,en"
            ]
        )
        
        # Rastgele ekran boyutları ve user agent seçimi
        context = browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
            device_scale_factor=random.choice([1, 2]),
            has_touch=False,
            is_mobile=False,
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            extra_http_headers={
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        # Bot algılamasını aşmak için ek scriptler (webdriver bayrağını siler)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        data = []

        try:
            for attempt in range(1, 4):
                try:
                    # Rastgele bir bekleme süresi (insan taklidi)
                    time.sleep(random.uniform(1.0, 3.0))

                    logger.info("Navigating to GreenMetric rankings page...")
                    page.goto(URL, wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_load_state("networkidle", timeout=30000)

                    table_selector = _wait_for_any_selector(page, TABLE_SELECTORS, timeout_per_selector=12000)
                    if not table_selector:
                        raise RuntimeError("Ranking table not found with known selectors.")
                    logger.info(f"Page loaded, table found with selector: {table_selector}")

                    logger.info(f"Filtering by country: {COUNTRY_FILTER_VALUE}")
                    if not _apply_country_filter(page, COUNTRY_FILTER_VALUE):
                        logger.warning("Country filter not found or target option missing; continuing without explicit filter.")

                    page.wait_for_timeout(2500)

                    logger.info("Setting table to show all entries...")
                    if not _expand_table_length(page, desired="500"):
                        logger.warning("Table length selector not found; continuing with default page size.")

                    page.wait_for_timeout(2500)

                    logger.info("Extracting data from table...")
                    data = _extract_rows(page, table_selector)
                    if data:
                        normalized_targets = {"turkey", "turkiye", "türkiye"}
                        filtered = []
                        for row in data:
                            country = str(row.get("country", "")).strip().lower()
                            if country in normalized_targets:
                                row.pop("country", None)
                                filtered.append(row)
                        data = filtered
                    logger.info(f"Extracted {len(data)} Turkish universities.")

                    if data:
                        break

                    if attempt < 3:
                        backoff = attempt * 2
                        logger.warning(f"No rows extracted on attempt {attempt}; retrying in {backoff}s...")
                        time.sleep(backoff)
                except Exception as e:
                    if attempt >= 3:
                        raise
                    backoff = attempt * 2
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {backoff}s...")
                    time.sleep(backoff)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            browser.close()

    if not data:
        logger.warning("No data extracted! Check if the site structure has changed.")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Rename columns for clarity in Excel
    df.columns = [
        "World Rank",
        "Country Rank",
        "University",
        "Total Score",
        "Setting & Infrastructure (SI)",
        "Energy & Climate Change (EC)",
        "Waste (WS)",
        "Water (WR)",
        "Transportation (TR)",
        "Education & Research (ED)"
    ]

    # Sort by World Rank
    df = df.sort_values("World Rank").reset_index(drop=True)

    return df


def save_to_excel(df: pd.DataFrame, filepath: str) -> None:
    """Save DataFrame to a formatted Excel file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="GreenMetric 2025")

        # Auto-adjust column widths
        worksheet = writer.sheets["GreenMetric 2025"]
        for col_idx, col_name in enumerate(df.columns, 1):
            max_length = max(
                len(str(col_name)),
                df[col_name].astype(str).str.len().max() if len(df) > 0 else 0
            )
            worksheet.column_dimensions[
                worksheet.cell(row=1, column=col_idx).column_letter
            ].width = min(max_length + 3, 50)

    logger.info(f"Excel file saved: {filepath}")


def save_to_json(df: pd.DataFrame, filepath: str) -> None:
    """Save DataFrame as JSON backup."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    records = df.to_dict(orient="records")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "source": "UI GreenMetric World University Rankings 2025",
            "country": "Turkiye",
            "scraped_at": datetime.now().isoformat(),
            "total_universities": len(records),
            "data": records
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON backup saved: {filepath}")


def run():
    """Main entry point for GreenMetric scraper."""
    logger.info("=" * 60)
    logger.info("UI GreenMetric Scraper - Turkish Universities")
    logger.info("=" * 60)

    df = scrape_greenmetric()

    if df.empty:
        logger.error("No data scraped. Aborting.")
        return None

    # Save outputs
    save_to_excel(df, OUTPUT_FILE)
    save_to_json(df, JSON_BACKUP)

    # Print summary
    logger.info(f"\n{'=' * 60}")
    logger.info(f"SUMMARY: {len(df)} Turkish universities scraped.")
    logger.info(f"Top 5 by World Rank:")
    top5 = df.head(5)[["World Rank", "University", "Total Score"]]
    for _, row in top5.iterrows():
        logger.info(f"  #{int(row['World Rank'])}: {row['University']} ({row['Total Score']})")
    logger.info(f"{'=' * 60}")

    return df


if __name__ == "__main__":
    run()

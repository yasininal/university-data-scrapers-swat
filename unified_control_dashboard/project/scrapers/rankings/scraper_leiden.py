"""
CWTS Leiden Ranking 2025 - Scraper
Extracts publication and citation data for Turkish universities
from traditional.leidenranking.com using Playwright.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
# from playwright.sync_api import sync_playwright
import pandas as pd

# ─── Configuration ───────────────────────────────────────────────────────────
BASE_URL = "https://traditional.leidenranking.com/ranking/2025/list"
COUNTRY_VALUE = "country-TR"  # Value in the continents-and-countries dropdown
ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "data" / "raw"
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = str(OUTPUT_DIR / f"leiden_turkey_{_ts}.xlsx")
JSON_BACKUP = str(OUTPUT_DIR / f"leiden_turkey_{_ts}.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

def scrape_leiden() -> pd.DataFrame:
    """
    Fetch Leiden Ranking data via HTTP POST for Turkey
    and extract publication/citation data parsing the HTML response.
    """
    logger.info("Starting Leiden Ranking scraper...")
    logger.info(f"Target URL: {BASE_URL}")

    url = 'https://traditional.leidenranking.com/Ranking2025/Ranking2025ListResult'
    payload = {
        'field_id': '1',
        'continent_code': '',
        'country_code': 'TR',
        'performance_dimension': '0',
        'ranking_indicator': '3',
        'fractional_counting': 'true',
        'core_pub_only': 'false',
        'number_of_publications': '100',
        'period_id': '15',
        'period_text': '2020–2023',
        'order_by': 'p'
    }
    encoded_args = urllib.parse.urlencode(payload).encode('utf-8')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*, text/html',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': BASE_URL,
        'Origin': 'https://traditional.leidenranking.com'
    }

    try:
        logger.info("Sending POST request (urllib) to Leiden API...")
        req = urllib.request.Request(url, data=encoded_args, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')

        logger.info("Parsing HTML response...")
        soup = BeautifulSoup(html, 'lxml')
        rows = soup.find_all('tr')
        
        data = []
        for index, row in enumerate(rows):
            cells = row.find_all('td')
            if len(cells) < 5:
                continue

            # Extract University Name
            uni_cell = cells[1]
            uni_name = uni_cell.get_text(separator=' ', strip=True).split('P:')[0].replace('Turkey', '').strip(' \t\n\r,-')

            # Extract P, P_top10, PP_top10 by finding the tooltips which contain the actual clean values
            def get_tooltip_val(cell):
                div = cell.find('div', attrs={'data-tooltip': True})
                if div:
                    tt = div['data-tooltip']
                    if '<b>' in tt and '</b>' in tt:
                        return tt.split('<b>')[1].split('</b>')[0].strip()
                return cell.get_text(strip=True)

            p = get_tooltip_val(cells[2])
            p_top10 = get_tooltip_val(cells[3])
            pp_top10 = get_tooltip_val(cells[4])
            
            rank = cells[0].get_text(strip=True) or str(index + 1)

            if uni_name:
                data.append({
                    'rank': rank,
                    'university': uni_name,
                    'p': p,
                    'p_top10': p_top10,
                    'pp_top10': pp_top10
                })

        logger.info(f"Extracted {len(data)} Turkish universities.")
        if len(data) > 0:
            logger.info(f"Sample raw data: {data[0]}")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return pd.DataFrame()

    if not data:
        logger.warning("No data extracted! Check if the site structure has changed.")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Clean numeric columns
    # P and P_top10 might have commas (e.g. "1,234")
    df["p"] = pd.to_numeric(df["p"].str.replace(",", "").str.strip(), errors="coerce")
    df["p_top10"] = pd.to_numeric(df["p_top10"].str.replace(",", "").str.strip(), errors="coerce")
    # pp_top10 might have "%" sign
    df["pp_top10"] = pd.to_numeric(df["pp_top10"].str.replace("%", "").str.strip(), errors="coerce")

    # Rename columns for Excel clarity
    df.columns = [
        "Rank",
        "University",
        "P (Publications)",
        "P(top 10%)",
        "PP(top 10%) %"
    ]

    # Sort by P (publications) descending
    df = df.sort_values("P (Publications)", ascending=False).reset_index(drop=True)
    df["Rank"] = range(1, len(df) + 1)

    return df


def save_to_excel(df: pd.DataFrame, filepath: str) -> None:
    """Save DataFrame to a formatted Excel file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Leiden 2025")

        # Auto-adjust column widths
        worksheet = writer.sheets["Leiden 2025"]
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
            "source": "CWTS Leiden Ranking Traditional Edition 2025",
            "country": "Turkey",
            "scraped_at": datetime.now().isoformat(),
            "total_universities": len(records),
            "indicators": {
                "P": "Total number of publications",
                "P(top 10%)": "Number of publications in top 10% by citations",
                "PP(top 10%)": "Proportion of publications in top 10%"
            },
            "data": records
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON backup saved: {filepath}")


def run():
    """Main entry point for Leiden scraper."""
    logger.info("=" * 60)
    logger.info("CWTS Leiden Ranking Scraper - Turkish Universities")
    logger.info("=" * 60)

    df = scrape_leiden()

    if df.empty:
        logger.error("No data scraped. Aborting.")
        return None

    # Save outputs
    save_to_excel(df, OUTPUT_FILE)
    save_to_json(df, JSON_BACKUP)

    # Print summary
    logger.info(f"\n{'=' * 60}")
    logger.info(f"SUMMARY: {len(df)} Turkish universities scraped.")
    logger.info(f"Top 5 by Publication Count:")
    top5 = df.head(5)[["Rank", "University", "P (Publications)", "PP(top 10%) %"]]
    for _, row in top5.iterrows():
        p_val = int(row['P (Publications)']) if pd.notna(row['P (Publications)']) else 'N/A'
        pp_val = row['PP(top 10%) %'] if pd.notna(row['PP(top 10%) %']) else 'N/A'
        logger.info(
            f"  #{int(row['Rank'])}: {row['University']} "
            f"(P={p_val}, PP(top 10%)={pp_val}%)"
        )
    logger.info(f"{'=' * 60}")

    return df


if __name__ == "__main__":
    run()

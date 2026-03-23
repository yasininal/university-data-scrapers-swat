"""
University Rankings Scraper
============================
- Shanghai ARWU  : Direct API call (fast, no browser needed)
- URAP Turkey    : Playwright with retries + robust network handling
                   Falls back to full table scrape if download button fails

Install:  pip install playwright requests openpyxl pandas
Browser:  playwright install chromium
Run:      python university_rankings_scraper.py
"""

import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CURRENT_YEAR   = datetime.now().year
YEAR_FALLBACKS = [CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2]
OUTPUT_DIR     = Path(__file__).resolve().parents[2] / "data" / "raw"
MAX_RETRIES    = 3   # retry each URL this many times on network error

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# SHANGHAI  (pure requests API — fast, no browser)
# ─────────────────────────────────────────────────────────────

def get_shanghai_rankings():
    print("\n" + "=" * 50)
    print("  SHANGHAI ARWU  (API mode)")
    print("=" * 50)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.shanghairanking.com/",
    }

    for year in YEAR_FALLBACKS:
        api_url = f"https://www.shanghairanking.com/api/pub/v1/arwu/rank?version={year}"
        print(f"[*] Trying year {year} ...")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(api_url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code} -- skipping year")
                    break

                data = resp.json()
                rankings_list = (
                    data.get("data", {}).get("rankings")
                    or data.get("data", {}).get("rank")
                    or (data["data"] if isinstance(data.get("data"), list) else None)
                )
                if not rankings_list:
                    print("    Empty payload -- skipping year")
                    break

                print(f"    Got {len(rankings_list)} total universities")
                df_all = pd.DataFrame(rankings_list)

                mask = df_all.astype(str).apply(
                    lambda col: col.str.contains(
                        r"turkey|turkiye|türkiye", case=False, na=False, regex=True
                    )
                ).any(axis=1)
                df_turkey = df_all[mask].copy()

                # Print all columns so user can verify
                print(f"    Available columns: {list(df_turkey.columns)}")
                # Pick exact columns: ranking, univNameEn, regionRank
                def pick_col(df, candidates):
                    for c in candidates:
                        if c in df.columns:
                            return c
                        matches = [x for x in df.columns if x.lower() == c.lower()]
                        if matches:
                            return matches[0]
                    return None

                rank_col   = pick_col(df_turkey, ["ranking", "rankPos", "rank", "worldRank", "world_rank"])
                name_col   = pick_col(df_turkey, ["univNameEn", "univName", "name", "university"])
                region_col = pick_col(df_turkey, ["regionRank", "region_rank", "regionRanking"])

                keep = {c: label for c, label in [
                    (rank_col,   "ranking"),
                    (name_col,   "univNameEn"),
                    (region_col, "regionRank"),
                ] if c is not None}

                print(f"     API columns available: {list(df_turkey.columns)}")
                print(f"     Matched: {keep}")
                df_turkey = df_turkey[list(keep.keys())].rename(columns=keep)
                out = OUTPUT_DIR / f"Shanghai_ARWU_Turkey_{year}.xlsx"
                df_turkey.to_excel(out, index=False)
                print(f"[OK] {len(df_turkey)} Turkish universities -> {out}")
                print(f"     Columns: {list(df_turkey.columns)}")
                return True

            except Exception as e:
                print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(3)

    print("[FAIL] No Shanghai data found.")
    return False


# ─────────────────────────────────────────────────────────────
# URAP  — robust loader with retries, then scrape table
# ─────────────────────────────────────────────────────────────

def _try_goto(page, url, retries=MAX_RETRIES):
    """Navigate with retries on network errors."""
    for attempt in range(1, retries + 1):
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            status = resp.status if resp else 0
            if status in (200, 304, 0):
                return True
            print(f"    HTTP {status}")
            return False
        except PWTimeout:
            print(f"    Timeout (attempt {attempt}/{retries})")
        except Exception as e:
            msg = str(e).split("\n")[0]
            print(f"    Network error (attempt {attempt}/{retries}): {msg}")
        if attempt < retries:
            print(f"    Waiting 5s before retry...")
            time.sleep(5)
    return False


def get_urap_rankings():
    print("\n" + "=" * 50)
    print("  URAP TURKEY  (table scrape)")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--ignore-certificate-errors",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
            ignore_https_errors=True,
        )
        page = context.new_page()
        # Abort images/fonts/media to speed up load and reduce flaky network
        page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,mp4,mp3}", lambda r: r.abort())

        for base_year in YEAR_FALLBACKS:
            next_year = base_year + 1
            url = f"https://newtr.urapcenter.org/Rankings/{base_year}-{next_year}/GENEL-SIRALAMASI-{base_year}"
            print(f"\n[*] Trying {base_year}-{next_year} ...")

            if not _try_goto(page, url):
                print("    Could not load page -- skipping year")
                continue

            # Extra wait for JS rendering
            page.wait_for_timeout(3_000)

            # Check page actually has content
            try:
                body_text = page.locator("body").inner_text(timeout=5_000)
                if len(body_text.strip()) < 100:
                    print("    Page appears blank -- skipping year")
                    continue
            except Exception:
                pass

            # Wait for table rows that actually contain text (not skeleton/empty rows)
            try:
                page.wait_for_selector("table tbody tr", timeout=20_000)
            except PWTimeout:
                print("    Table did not render -- skipping year")
                continue

            # Critical check: make sure rows have real data, not just an empty skeleton
            page.wait_for_timeout(2_000)  # let any lazy-render finish
            try:
                row_texts = page.locator("table tbody tr td").all_inner_texts()
                filled = [t.strip() for t in row_texts if t.strip()]
                if len(filled) < 5:
                    print(f"    Table rendered but has no data ({len(filled)} filled cells) -- skipping year")
                    continue
                print(f"    Table has data ({len(filled)} filled cells across rows)")
            except Exception as e:
                print(f"    Could not verify table data: {e} -- skipping year")
                continue

            print("    Attempting Excel button click first...")
            page.wait_for_timeout(2_000)

            # ── Try Excel button ──
            excel_selectors = [
                ".buttons-excel",
                "button.buttons-excel",
                "a.buttons-excel",
                ".dt-button.buttons-excel",
                "button:has-text('Excel')",
                "a:has-text('Excel')",
                "button:has-text('ndir')",   # covers İndir
                "a[href$='.xlsx']",
            ]
            btn = None
            for sel in excel_selectors:
                try:
                    c = page.locator(sel).first
                    if c.is_visible(timeout=800):
                        btn = c
                        print(f"    Found Excel button: {sel!r}")
                        break
                except Exception:
                    pass

            out_file = OUTPUT_DIR / f"URAP_Turkey_{base_year}-{next_year}.xlsx"

            if btn:
                try:
                    with page.expect_download(timeout=15_000) as dl_info:
                        btn.click(force=True)
                    dl_info.value.save_as(out_file)
                    print(f"[OK] Downloaded via button -> {out_file}")
                    browser.close()
                    return True
                except Exception as e:
                    print(f"    Button click failed ({e}) -- scraping table")

            # ── Scrape full table (all pages) ──
            print("    Scraping table...")
            rows = _scrape_all_pages(page)
            if rows:
                df = pd.DataFrame(rows)
                df.to_excel(out_file, index=False)
                print(f"[OK] Scraped {len(df)} rows -> {out_file}")
                browser.close()
                return True
            else:
                print("    No rows found -- skipping year")

        browser.close()
        print("\n[FAIL] No URAP data found for any year.")
        return False


def _scrape_all_pages(page) -> list[dict]:
    """Scrape all rows across DataTables pages."""
    all_rows = []

    # Try to show all rows at once
    try:
        sel = page.locator("select[name$='_length'], select[name*='DataTables']").first
        if sel.is_visible(timeout=2_000):
            sel.select_option("-1")
            page.wait_for_timeout(2_500)
            print("    Set table to show ALL rows")
    except Exception:
        pass

    seen_pages = set()
    while True:
        rows = _scrape_visible_rows(page)
        if not rows:
            break

        # Use first row as a fingerprint to detect loops
        fingerprint = str(rows[0])
        if fingerprint in seen_pages:
            break
        seen_pages.add(fingerprint)
        all_rows.extend(rows)

        # Try next page button
        try:
            nxt = page.locator(
                "#DataTables_Table_0_next:not(.disabled), "
                "a.paginate_button.next:not(.disabled), "
                "li.next:not(.disabled) a"
            ).first
            if nxt.count() and nxt.is_visible(timeout=500):
                nxt.click()
                page.wait_for_timeout(800)
            else:
                break
        except Exception:
            break

    return all_rows


def _scrape_visible_rows(page) -> list[dict]:
    rows = []
    try:
        headers = [
            h.strip() for h in page.locator("table thead th").all_inner_texts()
        ]
        if not headers:
            headers = [f"col_{i}" for i in range(20)]

        for tr in page.locator("table tbody tr").all():
            cells = tr.locator("td").all_inner_texts()
            row = {
                (headers[i] if i < len(headers) else f"col_{i}"): v.strip()
                for i, v in enumerate(cells)
            }
            if any(row.values()):
                rows.append(row)
    except Exception as e:
        print(f"    Row parse error: {e}")
    return rows


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Run date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Year scan: {YEAR_FALLBACKS}")

    shanghai_ok = get_shanghai_rankings()
    urap_ok     = get_urap_rankings()

    print("\n" + "=" * 50)
    print(f"  Shanghai ARWU : {'OK' if shanghai_ok else 'FAILED'}")
    print(f"  URAP Turkey   : {'OK' if urap_ok     else 'FAILED'}")
    print("=" * 50)
"""Scraper for Yatırıma Destek (Investment Support) Portal"""

import logging
import requests
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
import re
from .base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class YatirimaDestekScraper(BaseScraper):
    """
    Scraper for Yatırıma Destek Portalı.

    The main /destek-arama page is JS-rendered, so we fall back to the
    static sitemap-style listing pages that are server-side rendered.
    """

    # Static pages with support program listings
    STATIC_PAGES = [
        "https://www.yatirimadestek.gov.tr/destekler",
        "https://www.yatirimadestek.gov.tr/hibe-destekleri",
        "https://www.yatirimadestek.gov.tr/finansman-destekleri",
        "https://www.yatirimadestek.gov.tr/vergi-destekleri",
        "https://www.yatirimadestek.gov.tr/destek-programlari",
    ]

    # Fallback: KOSGEB hibe çağrıları (static, well-structured)
    KOSGEB_URL = "https://www.kosgeb.gov.tr/site/tr/genel/destekler/0/destekler"

    def __init__(self):
        super().__init__(
            source_name="Yatırıma Destek Portalı",
            source_url="https://www.yatirimadestek.gov.tr",
            timeout=30,
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Try each static page in order; collect all found grants.
        Falls back to KOSGEB if the main portal returns nothing.
        """
        grants = []
        seen_urls: set = set()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        }

        for url in self.STATIC_PAGES:
            try:
                logger.info(f"Fetching {url}")
                response = requests.get(url, headers=headers, timeout=self.timeout)
                if response.status_code == 404:
                    logger.debug(f"404 — skipping {url}")
                    continue
                response.raise_for_status()
                response.encoding = "utf-8"

                soup = BeautifulSoup(response.content, "lxml")
                page_grants = self._parse_page(soup, base_url=url)

                for g in page_grants:
                    if g["url"] not in seen_urls:
                        seen_urls.add(g["url"])
                        grants.append(g)

            except requests.RequestException as e:
                logger.debug(f"Request error for {url}: {e}")
                continue

        # If portal returned nothing, try KOSGEB as a supplementary source
        if not grants:
            logger.info("Main portal returned nothing — trying KOSGEB fallback")
            try:
                response = requests.get(
                    self.KOSGEB_URL, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                soup = BeautifulSoup(response.content, "lxml")
                grants = self._parse_kosgeb(soup)
            except Exception as e:
                logger.debug(f"KOSGEB fallback failed: {e}")

        logger.info(f"Yatırıma Destek total: {len(grants)} grants found")
        return grants

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Generic parser — extracts all meaningful support program links."""
        grants = []

        # Try structured cards/items first
        for selector in [
            "article",
            ".card",
            ".destek-item",
            ".program-item",
            ".support-item",
            "li.list-group-item",
        ]:
            items = soup.select(selector)
            for item in items:
                g = self._parse_structured_item(item, base_url)
                if g:
                    grants.append(g)
            if grants:
                return grants

        # Fallback: scan all links with relevant keywords
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            text = link.get_text(strip=True)

            if len(text) < 15:
                continue

            keywords = [
                "destek", "hibe", "finansman", "kredi", "teşvik",
                "program", "çağrı", "fon", "yatırım",
            ]
            if not any(kw in text.lower() for kw in keywords):
                continue

            url = self._abs_url(href, "https://www.yatirimadestek.gov.tr")
            if not url:
                continue

            grants.append({
                "call_title": text[:200],
                "url": url,
                "program_name": "Yatırıma Destek Programı",
                "sector": self._infer_sector(text),
            })

        return grants

    def _parse_structured_item(
        self, item: BeautifulSoup, base_url: str
    ) -> Dict[str, Any] | None:
        """Parse a single card/article element."""
        title_el = item.find(["h2", "h3", "h4", "h5", "strong"])
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        if len(title) < 10:
            return None

        link = item.find("a", href=True)
        if not link:
            return None

        url = self._abs_url(link["href"], "https://www.yatirimadestek.gov.tr")
        if not url:
            return None

        grant: Dict[str, Any] = {
            "call_title": title[:200],
            "url": url,
            "program_name": "Yatırıma Destek Programı",
            "sector": self._infer_sector(title),
        }

        # Description
        desc = item.find(["p", "div"], class_=re.compile(r"desc|summary|excerpt|text"))
        if desc:
            grant["description"] = desc.get_text(strip=True)[:500]

        # Deadline
        deadline = self._extract_deadline(item.get_text())
        if deadline:
            grant["deadline"] = deadline

        return grant

    def _parse_kosgeb(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse KOSGEB support programs page."""
        grants = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"].strip()

            if len(text) < 15:
                continue
            if not any(kw in text.lower() for kw in ["destek", "hibe", "program", "fon"]):
                continue

            url = self._abs_url(href, "https://www.kosgeb.gov.tr")
            if not url:
                continue

            grants.append({
                "call_title": text[:200],
                "url": url,
                "program_name": "KOSGEB Destek Programları",
                "sector": self._infer_sector(text),
                "source_name": "KOSGEB",
            })

        return grants

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _abs_url(self, href: str, base: str) -> str | None:
        """Make a URL absolute; return None if clearly invalid."""
        href = href.strip()
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            return None
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return base.rstrip("/") + href
        return base.rstrip("/") + "/" + href

    def _extract_deadline(self, text: str) -> datetime | None:
        """Try to extract a deadline date from free text."""
        patterns = [
            r"(?:son\s+tarih|kapanış|başvuru\s+sonu)[\s:]*(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})",
            r"(\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+\d{4})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    ds = m.group(1)
                    if "/" in ds or "." in ds:
                        return datetime.strptime(ds.replace(".", "/"), "%d/%m/%Y")
                    return self._parse_turkish_date(ds)
                except (ValueError, TypeError):
                    pass
        return None

    def _infer_sector(self, text: str) -> str:
        text_lower = text.lower()
        sectors = {
            "İmalat": ["imalat", "üretim", "sanayi", "makine"],
            "Ar-Ge": ["ar-ge", "araştırma", "geliştirme", "inovasyon"],
            "Tarım": ["tarım", "hayvancılık", "su ürünleri"],
            "Turizm": ["turizm", "otelcilik", "restoran"],
            "Teknoloji": ["teknoloji", "yazılım", "dijital", "bilişim"],
            "Eğitim": ["eğitim", "öğretim", "okul"],
            "Sağlık": ["sağlık", "tıbbi", "ilaç"],
            "Enerji": ["enerji", "elektrik", "yenilenebilir"],
            "Ulaştırma": ["ulaştırma", "lojistik", "depo"],
        }
        for sector, keywords in sectors.items():
            if any(kw in text_lower for kw in keywords):
                return sector
        return "Genel"

    def _parse_turkish_date(self, date_str: str) -> datetime | None:
        months = {
            "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
            "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
            "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
        }
        parts = date_str.split()
        if len(parts) < 3:
            return None
        try:
            day = int(parts[0])
            month = months.get(parts[1].lower())
            year = int(parts[2])
            if month:
                return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        return None

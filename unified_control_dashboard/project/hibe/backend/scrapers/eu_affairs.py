"""Scraper for AB Bakanlığı (Ministry of Foreign Affairs) current grants"""

import logging
import requests
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
import re
from .base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class EUAffairsScraper(BaseScraper):
    """Scraper for AB Bakanlığı Güncel Hibeler (current grants)"""

    def __init__(self):
        super().__init__(
            source_name="AB Bakanlığı Güncel Hibeler",
            source_url="https://www.ab.gov.tr/guncel-hibeler_4.html",
            timeout=30,
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape from AB Bakanlığı website using BeautifulSoup.
        """
        grants = []

        try:
            logger.info(f"Fetching {self.source_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(self.source_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for grant listings - typically in lists or divs
            # AB Bakanlığı uses a specific structure, look for main content area
            main_content = soup.find("main") or soup.find("div", class_="content")

            if not main_content:
                main_content = soup.find("body")

            if main_content:
                # Look for links that appear to be grant listings
                # These are usually in <a> or <h> tags with descriptive text
                for link in main_content.find_all("a"):
                    try:
                        href = link.get("href", "").strip()
                        text = link.get_text(strip=True)

                        # Filter for grant-like content
                        if not href or len(text) < 10:
                            continue

                        # Skip navigation links
                        if any(skip in text.lower() for skip in ["menu", "anasayfa", "geri", "ileri"]):
                            continue

                        # Try to extract deadline and other info from page text
                        grant = self._parse_grant(text, href, soup)
                        if grant:
                            grants.append(grant)

                    except Exception as e:
                        logger.debug(f"Error parsing AB grant link: {e}")
                        continue

            # Alternative: Look for table-based listings
            tables = main_content.find_all("table") if main_content else []
            for table in tables:
                try:
                    rows = table.find_all("tr")
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            grant = self._parse_table_row(cells, soup)
                            if grant:
                                grants.append(grant)
                except Exception as e:
                    logger.debug(f"Error parsing AB grant table: {e}")

        except requests.RequestException as e:
            logger.error(f"Request error from AB Bakanlığı: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping AB Bakanlığı: {e}")

        return grants

    def _parse_grant(self, text: str, href: str, page_soup) -> Dict[str, Any]:
        """
        Parse grant information from link text and href.

        Args:
            text: Link text content
            href: Link href attribute
            page_soup: Full page soup for context

        Returns:
            Parsed grant dictionary or None
        """
        # Ensure URL is absolute
        if href.startswith("/"):
            href = "https://www.ab.gov.tr" + href
        elif not href.startswith("http"):
            href = "https://www.ab.gov.tr/" + href

        grant = {
            "call_title": text[:200],
            "url": href,
            "program_name": "AB Bakanlığı Hibe Programı",
        }

        # Try to extract deadline from visible page text
        # Look for patterns like "Son Tarih: DD.MM.YYYY" or "Kapanış: DD/MM/YYYY"
        deadline_patterns = [
            r"(?:son\s+tarih|kapanış|başvuru\s+sonu)[\s:]*(\d{1,2}[./]\d{1,2}[./]\d{4})",
        ]

        page_text = page_soup.get_text()
        for pattern in deadline_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Parse DD.MM.YYYY or DD/MM/YYYY format
                    deadline = datetime.strptime(date_str.replace(".", "/").replace("-", "/"), "%d/%m/%Y")
                    grant["deadline"] = deadline
                    break
                except ValueError:
                    pass

        # Add sector based on keywords in title
        title_lower = text.lower()
        if any(keyword in title_lower for keyword in ["gençlik", "eğitim"]):
            grant["sector"] = "Eğitim"
        elif any(keyword in title_lower for keyword in ["araştırma", "ar-ge"]):
            grant["sector"] = "Ar-Ge"
        elif any(keyword in title_lower for keyword in ["kültür", "sanat"]):
            grant["sector"] = "Kültür ve Sanat"
        elif any(keyword in title_lower for keyword in ["çevre", "iklim"]):
            grant["sector"] = "Çevre"
        else:
            grant["sector"] = "Uluslararası"

        return grant

    def _parse_table_row(self, cells: List, page_soup) -> Dict[str, Any]:
        """
        Parse grant from table row cells.

        Args:
            cells: List of table cells
            page_soup: Full page soup for context

        Returns:
            Parsed grant dictionary or None
        """
        try:
            title = cells[0].get_text(strip=True)
            if len(title) < 10:
                return None

            # Look for link in cells
            link = cells[0].find("a")
            url = link.get("href") if link else None

            if not url:
                return None

            if url.startswith("/"):
                url = "https://www.ab.gov.tr" + url
            elif not url.startswith("http"):
                url = "https://www.ab.gov.tr/" + url

            grant = {
                "call_title": title[:200],
                "url": url,
                "program_name": "AB Bakanlığı Hibe Programı",
                "sector": "Uluslararası",
            }

            # Try to get deadline from second column
            if len(cells) > 1:
                deadline_text = cells[1].get_text(strip=True)
                try:
                    deadline = datetime.strptime(deadline_text.replace(".", "/"), "%d/%m/%Y")
                    grant["deadline"] = deadline
                except (ValueError, TypeError):
                    pass

            return grant
        except Exception as e:
            logger.debug(f"Error parsing table row: {e}")
            return None

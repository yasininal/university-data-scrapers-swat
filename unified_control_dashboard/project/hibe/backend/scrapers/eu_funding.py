"""Scraper for EU Funding & Tenders Portal API"""

import logging
import requests
from typing import List, Dict, Any
from datetime import datetime
from .base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class EUFundingScraper(BaseScraper):
    """Scraper for EU Funding & Tenders Portal using their public API"""

    API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    API_KEY = "SEDIA"  # Public API key from EU Commission

    def __init__(self):
        super().__init__(
            source_name="EU Funding & Tenders Portal",
            source_url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            timeout=30,
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape from EU Funding & Tenders API.
        The SEDIA search API requires a POST request with a JSON body.
        """
        grants = []

        try:
            # API requires POST with JSON body
            payload = {
                "query": "*",
                "pageSize": 100,
                "pageNumber": 1,
                "sortOrder": "DESC",
                "openCallsOnly": True,
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "apiKey": self.API_KEY,
            }

            logger.info(f"POST {self.API_URL}")
            response = requests.post(
                self.API_URL, json=payload, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            # API may return results under different keys
            results = (
                data.get("results")
                or data.get("items")
                or data.get("hits", {}).get("hits", [])
                or []
            )
            logger.info(f"EU API returned {len(results)} results")

            for item in results:
                try:
                    grant = self._parse_grant(item)
                    if grant:
                        grants.append(grant)
                except Exception as e:
                    logger.debug(f"Error parsing EU grant: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"Request error from EU Funding API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping EU Funding: {e}")

        return grants

    def _parse_grant(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single item from the EU API response.

        Args:
            item: JSON object from API

        Returns:
            Parsed grant dictionary
        """
        # Extract key fields from EU API response
        title = item.get("title", "").strip()
        identifier = item.get("identifier", "").strip()
        url = item.get("url", "").strip()

        # EU API doesn't always provide direct URLs, construct if needed
        if not url and identifier:
            url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search?recipientType=&callIdentifier={identifier}"

        if not url:
            return None

        # Parse deadline
        deadline = None
        deadline_str = item.get("deadlineDate")
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Budget information
        budget_amount = None
        budget_currency = "EUR"
        budget_info = item.get("budget")
        if budget_info:
            try:
                if isinstance(budget_info, (int, float)):
                    budget_amount = float(budget_info)
                elif isinstance(budget_info, dict):
                    budget_amount = float(budget_info.get("amount", 0))
            except (ValueError, TypeError):
                pass

        # Extract program/framework
        program_name = item.get("programmeName") or item.get("frameworkProgramme", "Horizon Europe")

        # Description
        description = item.get("description", "").strip() or item.get("shortDescription", "").strip()

        # Sector/classification
        sector = None
        if "cluster" in item:
            sector = item.get("cluster")
        elif "type" in item:
            sector = item.get("type")

        return {
            "original_id": identifier,
            "program_name": program_name,
            "call_title": title,
            "url": url,
            "deadline": deadline,
            "budget_amount": budget_amount,
            "budget_currency": budget_currency,
            "description": description,
            "sector": sector,
        }

"""Abstract base class for all scrapers"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for grant opportunity scrapers"""

    def __init__(self, source_name: str, source_url: str, timeout: int = 30):
        """
        Initialize the scraper.

        Args:
            source_name: Display name of the source
            source_url: URL of the source
            timeout: Request timeout in seconds
        """
        self.source_name = source_name
        self.source_url = source_url
        self.timeout = timeout

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape grant opportunities from the source.

        Returns:
            List of grant opportunity dictionaries with keys:
            - program_name: Program name (str)
            - call_title: Call/opportunity title (str, required)
            - url: Direct link to the opportunity (str, required)
            - deadline: Deadline date (datetime, optional)
            - budget_amount: Budget amount (float, optional)
            - budget_currency: Currency code (str, optional)
            - description: Description (str, optional)
            - eligibility_criteria: Eligibility info (str, optional)
            - sector: Sector/category (str, optional)
            - original_id: ID from source (str, optional)

        Raises:
            Exception: If scraping fails, should log and return empty list
        """
        pass

    def _validate_grant(self, grant: Dict[str, Any]) -> bool:
        """
        Validate that a grant has required fields.

        Args:
            grant: Grant dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["call_title", "url"]
        if not all(field in grant and grant[field] for field in required_fields):
            logger.warning(f"Invalid grant missing required fields: {grant}")
            return False
        return True

    def _normalize_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize grant data to standard format.

        Args:
            grant: Raw grant data

        Returns:
            Normalized grant dictionary
        """
        normalized = {
            "original_id": grant.get("original_id"),
            "program_name": grant.get("program_name", "").strip() or None,
            "call_title": grant.get("call_title", "").strip(),
            "url": grant.get("url", "").strip(),
            "deadline": grant.get("deadline"),
            "budget_amount": grant.get("budget_amount"),
            "budget_currency": grant.get("budget_currency"),
            "sector": grant.get("sector", "").strip() or None,
            "description": grant.get("description", "").strip() or None,
            "eligibility_criteria": grant.get("eligibility_criteria", "").strip() or None,
        }
        return normalized

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Main entry point that handles error catching and normalization.

        Returns:
            List of normalized grant dictionaries
        """
        try:
            logger.info(f"Starting scrape of {self.source_name}")
            grants = self.scrape()

            # Normalize and validate
            validated_grants = []
            for grant in grants:
                normalized = self._normalize_grant(grant)
                if self._validate_grant(normalized):
                    validated_grants.append(normalized)
                else:
                    logger.debug(f"Skipped invalid grant: {grant}")

            logger.info(f"Successfully scraped {len(validated_grants)} opportunities from {self.source_name}")
            return validated_grants

        except Exception as e:
            logger.error(f"Error scraping {self.source_name}: {str(e)}", exc_info=True)
            return []

"""Scrapers package for Grant Dashboard"""

from .base_scraper import BaseScraper
from .eu_funding import EUFundingScraper
from .eu_affairs import EUAffairsScraper
from .yatirima_destek import YatirimaDestekScraper

__all__ = [
    "BaseScraper",
    "EUFundingScraper",
    "EUAffairsScraper",
    "YatirimaDestekScraper",
]

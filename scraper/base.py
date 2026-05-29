import requests
from abc import ABC, abstractmethod
from loguru import logger


class BaseScraper(ABC):
    """Base class for all site-specific scrapers."""

    def __init__(self, source: dict):
        self.name = source["name"]
        self.url = source["url"]
        self.opportunity_type = source["type"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })

    def fetch(self, url: str = None) -> str:
        target = url or self.url
        logger.debug(f"Fetching {target}")
        response = self.session.get(target, timeout=30)
        response.raise_for_status()
        return response.text

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of opportunity dicts from this source."""
        ...

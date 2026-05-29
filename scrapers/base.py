from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import requests
from loguru import logger


@dataclass
class FacultyData:
    """Normalized data for a single faculty member, returned by faculty scrapers."""
    name: str
    profile_url: str
    title: str = ""
    department: str = ""
    school: str = "Michigan Medicine"
    research_interests: str = ""   # comma-separated keywords or free text
    lab_assets: str = ""
    project_ideas: str = ""
    email: str = ""
    phone: str = ""
    raw_data: str = ""


@dataclass
class OpportunityData:
    """Normalized data for a single opportunity, returned by any scraper."""
    title: str
    url: str
    description: str = ""
    company_name: str = ""
    opportunity_type: str = ""       # pre-classified by scraper if source makes it obvious
    therapeutic_area: str = ""       # pre-classified by scraper if source makes it obvious
    funding_amount: str = ""
    deadline: Optional[datetime] = None
    contact_info: str = ""
    raw_data: str = ""               # JSON string of original API response


class BaseScraper(ABC):
    """
    Abstract base for all source scrapers.

    Subclasses implement `scrape()` and return a list of OpportunityData objects.
    The runner in services/scrape_runner.py handles persistence and deduplication.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/html, */*",
    }

    def __init__(self, source_site):
        self.source_site = source_site
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    @abstractmethod
    def scrape(self) -> list[OpportunityData]:
        """Fetch and return opportunities from this source. Must not raise — log and return []."""
        ...

    def get(self, url: str, **kwargs) -> requests.Response:
        logger.debug(f"GET {url}")
        resp = self.session.get(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    def post(self, url: str, **kwargs) -> requests.Response:
        logger.debug(f"POST {url}")
        resp = self.session.post(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    @staticmethod
    def parse_date(value: Optional[str], fmt: str = "%m/%d/%Y") -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            return None

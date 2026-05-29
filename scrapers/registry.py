"""
Scraper registry — maps scraper_key strings (stored in source_sites.scraper_key)
to the concrete scraper class that handles that source.

To add a new source:
  1. Create scrapers/my_source.py with a class inheriting BaseScraper
  2. Add an entry here: "my_key": MySourceScraper
  3. Add a row in config/sources.yaml with scraper_key: my_key
"""
from scrapers.clinicaltrials import ClinicalTrialsScraper
from scrapers.grants_gov import GrantsGovScraper
from scrapers.nih_guide import NIHGuideScraper
from scrapers.sbir_gov import SBIRGovScraper
from scrapers.wellcome import WellcomeTrustScraper
from scrapers.rwjf import RWJFScraper

REGISTRY: dict[str, type] = {
    "clinicaltrials": ClinicalTrialsScraper,
    "grants_gov": GrantsGovScraper,
    "nih_guide": NIHGuideScraper,
    "sbir_gov": SBIRGovScraper,
    "wellcome": WellcomeTrustScraper,
    "rwjf": RWJFScraper,
}


def get_scraper(scraper_key: str, source_site):
    """Return an instantiated scraper for the given key, or None if unknown."""
    cls = REGISTRY.get(scraper_key)
    if cls is None:
        return None
    return cls(source_site)

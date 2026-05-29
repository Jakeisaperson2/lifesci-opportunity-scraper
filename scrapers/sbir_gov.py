"""
SBIR.gov solicitations scraper.
API: https://api.sbir.gov/public/api/solicitations

SBIR/STTR are federally-mandated R&D programs where small companies
(pharma, biotech, medtech startups) are funded to conduct research —
often requiring or preferring academic medical center collaborators
for clinical and translational components.
"""
import json
from datetime import datetime
from typing import Optional
from loguru import logger
from scrapers.base import BaseScraper, OpportunityData


class SBIRGovScraper(BaseScraper):

    API_URL = "https://api.sbir.gov/public/api/solicitations"

    SEARCH_KEYWORDS = [
        "biomedical",
        "clinical research",
        "pharmaceutical",
        "oncology",
        "drug development",
        "medical device",
        "translational",
    ]

    def scrape(self) -> list[OpportunityData]:
        results: list[OpportunityData] = []
        seen_ids: set[str] = set()

        for keyword in self.SEARCH_KEYWORDS:
            try:
                batch = self._search(keyword, seen_ids)
                results.extend(batch)
                logger.debug(f"SBIR.gov '{keyword}': {len(batch)} new results")
            except Exception as e:
                logger.error(f"SBIR.gov failed for keyword '{keyword}': {e}")

        logger.info(f"SBIR.gov: found {len(results)} opportunities total")
        return results

    def _search(self, keyword: str, seen_ids: set) -> list[OpportunityData]:
        params = {
            "keyword": keyword,
            "rows": 25,
            "start": 0,
            "currentStatus": "open",
        }
        resp = self.get(self.API_URL, params=params)
        data = resp.json()
        return self._parse(data, seen_ids)

    def _parse(self, data, seen_ids: set) -> list[OpportunityData]:
        opportunities = []

        # API may return a list directly or wrap results under a key
        if isinstance(data, list):
            items = data
        else:
            items = data.get("solicitations", data.get("data", data.get("results", [])))

        for item in items:
            sol_id = str(item.get("solicitation_id") or item.get("id") or "")
            if not sol_id or sol_id in seen_ids:
                continue
            seen_ids.add(sol_id)

            title = (item.get("solicitation_title") or item.get("title") or "").strip()
            if not title:
                continue

            agency = item.get("agency", "")
            branch = item.get("branch", "")
            program = item.get("program", "SBIR")
            phase = item.get("phase", "")

            url = (
                item.get("solicitation_agency_url")
                or item.get("url")
                or f"https://www.sbir.gov/node/{sol_id}"
            )

            funding_raw = (
                item.get("funding_amount")
                or item.get("award_amount")
                or item.get("awardCeiling")
                or item.get("award_ceiling")
                or ""
            )
            funding = str(funding_raw).strip() if funding_raw else ""

            close_date = self._parse_sbir_date(
                item.get("close_date") or item.get("closeDate") or ""
            )

            description = (
                item.get("description_content")
                or item.get("description")
                or item.get("abstract")
                or ""
            )

            phase_tag = f" Phase {phase}" if phase else ""
            display_title = f"[{program}{phase_tag}] {title}"

            opp = OpportunityData(
                title=display_title,
                url=url,
                description=str(description)[:1000],
                company_name=f"{agency} – {branch}" if branch else agency,
                opportunity_type="grant",
                funding_amount=funding,
                deadline=close_date,
                raw_data=json.dumps({
                    "id": sol_id,
                    "program": program,
                    "phase": phase,
                    "agency": agency,
                    "branch": branch,
                }),
            )
            opportunities.append(opp)

        return opportunities

    def _parse_sbir_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%m-%d-%Y"):
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except (ValueError, AttributeError):
                continue
        return None

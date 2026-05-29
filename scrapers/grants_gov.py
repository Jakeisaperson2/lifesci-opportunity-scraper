"""
Grants.gov REST API scraper.

Searches the federal grants database for life-sciences related funding
opportunities. Grants.gov aggregates postings from NIH, BARDA, NSF, DOD,
FDA, and all other federal agencies — making it the broadest single source
for public research funding calls.

API reference: https://www.grants.gov/web/grants/search-grants.html
Endpoint: POST https://apply07.grants.gov/grantsws/rest/opportunities/search/
"""
import json
from loguru import logger
from scrapers.base import BaseScraper, OpportunityData


class GrantsGovScraper(BaseScraper):
    API_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search/"

    # Targeted keywords for life sciences / academic medical center opportunities
    SEARCH_KEYWORDS = [
        "clinical trial research",
        "biomedical research collaboration",
        "translational research",
        "drug development partnership",
        "investigator initiated",
        "oncology research",
        "health data AI",
    ]

    def scrape(self) -> list[OpportunityData]:
        results: list[OpportunityData] = []
        seen_ids: set[str] = set()

        for keyword in self.SEARCH_KEYWORDS:
            try:
                batch = self._search(keyword, seen_ids)
                results.extend(batch)
                logger.debug(f"Grants.gov '{keyword}': {len(batch)} new results")
            except Exception as e:
                logger.error(f"Grants.gov failed for keyword '{keyword}': {e}")

        logger.info(f"Grants.gov: found {len(results)} opportunities")
        return results

    def _search(self, keyword: str, seen_ids: set) -> list[OpportunityData]:
        payload = {
            "keyword": keyword,
            "oppNum": "",
            "cfda": "",
            "agency": "",
            "startFrom": 0,
            "rows": 25,
            "sortBy": "openDate|desc",
            "status": ["posted", "forecasted"],
        }
        resp = self.post(self.API_URL, json=payload)
        data = resp.json()
        return self._parse(data, seen_ids)

    def _parse(self, data: dict, seen_ids: set) -> list[OpportunityData]:
        opportunities = []
        for hit in data.get("oppHits", []):
            opp_id = str(hit.get("id", ""))
            if not opp_id or opp_id in seen_ids:
                continue
            seen_ids.add(opp_id)

            opp_number = hit.get("number", "")
            title = hit.get("title", "").strip()
            agency = hit.get("agency", "").strip()
            doc_type = hit.get("docType", "").lower()
            close_date = self.parse_date(hit.get("closeDate"))
            open_date = hit.get("openDate", "")

            # Map Grants.gov document types to our internal types
            if "rfp" in doc_type or "solicitation" in doc_type:
                opp_type = "rfp"
            elif "grant" in doc_type or "synopsis" in doc_type:
                opp_type = "grant"
            else:
                opp_type = "grant"

            opp = OpportunityData(
                title=f"{title} ({opp_number})" if opp_number else title,
                url=f"https://www.grants.gov/search-results-detail/{opp_id}",
                description=hit.get("synopsis", hit.get("description", ""))[:1000],
                company_name=agency,
                opportunity_type=opp_type,
                funding_amount=hit.get("awardCeiling", ""),
                deadline=close_date,
                raw_data=json.dumps({
                    "id": opp_id,
                    "number": opp_number,
                    "agency": agency,
                    "openDate": open_date,
                    "docType": doc_type,
                }),
            )
            opportunities.append(opp)

        return opportunities

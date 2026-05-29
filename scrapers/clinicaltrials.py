"""
ClinicalTrials.gov API v2 scraper.

Targets industry-sponsored interventional studies that are actively recruiting
or not yet recruiting — the primary signal that a pharma/biotech company is
seeking academic research sites or investigators.

API docs: https://clinicaltrials.gov/data-api/api
"""
import json
from loguru import logger
from scrapers.base import BaseScraper, OpportunityData


class ClinicalTrialsScraper(BaseScraper):
    API_URL = "https://clinicaltrials.gov/api/v2/studies"

    # Fields we actually use — requesting only what we need keeps responses fast
    FIELDS = ",".join([
        "NCTId",
        "BriefTitle",
        "BriefSummary",
        "LeadSponsorName",
        "LeadSponsorClass",
        "CollaboratorName",
        "Condition",
        "OverallStatus",
        "Phase",
        "StartDate",
        "PrimaryCompletionDate",
        "PointOfContactEMail",
        "CentralContactEMail",
        "StudyType",
        "FunderType",
    ])

    # Life-sciences search terms that indicate opportunities for academic sites
    SEARCH_TERMS = [
        "investigator initiated",
        "site selection",
        "research collaboration",
        "sponsored research",
    ]

    def scrape(self) -> list[OpportunityData]:
        results: list[OpportunityData] = []
        seen_ids: set[str] = set()

        # First pass: industry-sponsored recruiting trials (broadest signal)
        try:
            results.extend(self._fetch_industry_sponsored(seen_ids))
        except Exception as e:
            logger.error(f"ClinicalTrials industry-sponsored fetch failed: {e}")

        # Second pass: trials matching collaboration keywords
        for term in self.SEARCH_TERMS:
            try:
                results.extend(self._fetch_by_term(term, seen_ids))
            except Exception as e:
                logger.error(f"ClinicalTrials term '{term}' fetch failed: {e}")

        logger.info(f"ClinicalTrials: found {len(results)} opportunities")
        return results

    def _fetch_industry_sponsored(self, seen_ids: set) -> list[OpportunityData]:
        params = {
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "filter.studyType": "INTERVENTIONAL",
            "aggFilters": "funderType:INDUSTRY",
            "pageSize": 50,
            "fields": self.FIELDS,
            "sort": "LastUpdatePostDate:desc",
        }
        return self._fetch_page(params, seen_ids)

    def _fetch_by_term(self, term: str, seen_ids: set) -> list[OpportunityData]:
        params = {
            "query.term": term,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "filter.studyType": "INTERVENTIONAL",
            "pageSize": 25,
            "fields": self.FIELDS,
        }
        return self._fetch_page(params, seen_ids)

    def _fetch_page(self, params: dict, seen_ids: set) -> list[OpportunityData]:
        resp = self.get(self.API_URL, params=params)
        data = resp.json()
        opportunities = []

        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            nct_id = id_module.get("nctId", "")

            if not nct_id or nct_id in seen_ids:
                continue
            seen_ids.add(nct_id)

            desc_module = proto.get("descriptionModule", {})
            status_module = proto.get("statusModule", {})
            sponsor_module = proto.get("sponsorCollaboratorsModule", {})
            conditions_module = proto.get("conditionsModule", {})
            contacts_module = proto.get("contactsLocationsModule", {})

            lead_sponsor = sponsor_module.get("leadSponsor", {})
            company = lead_sponsor.get("name", "")

            # Collect contact emails if present
            contact_info = ""
            central = contacts_module.get("centralContacts", [])
            if central:
                emails = [c.get("email", "") for c in central if c.get("email")]
                contact_info = "; ".join(emails)

            conditions = conditions_module.get("conditions", [])
            therapeutic_area = ", ".join(conditions[:3]) if conditions else ""

            phase = status_module.get("phase", "")
            title = id_module.get("briefTitle", "")
            if phase:
                title = f"[{phase}] {title}"

            opp = OpportunityData(
                title=title,
                url=f"https://clinicaltrials.gov/study/{nct_id}",
                description=desc_module.get("briefSummary", "")[:1000],
                company_name=company,
                opportunity_type="clinical_trial",
                therapeutic_area=therapeutic_area,
                contact_info=contact_info,
                raw_data=json.dumps({"nct_id": nct_id, "sponsor": company, "conditions": conditions}),
            )
            opportunities.append(opp)

        return opportunities

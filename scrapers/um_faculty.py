"""
University of Michigan — Michigan Medicine faculty scraper.
Source: NIH Research Portfolio Online Reporting Tools (NIH Reporter) API
API docs: https://api.reporter.nih.gov

Queries NIH Reporter for recent U-M funded projects, then deduplicates
by PI profile_id so each researcher appears once. Accumulates their MeSH
research terms across all active grants to build a rich interest profile.

This is more useful than a raw faculty directory: it surfaces researchers
who are actively winning NIH funding — the ideal candidates for industry
partnership proposals.
"""
import json
from collections import defaultdict
from loguru import logger
from scrapers.base import BaseScraper, FacultyData

API_URL = "https://api.reporter.nih.gov/v2/projects/search"
REPORTER_PROFILE_URL = "https://reporter.nih.gov/search/{search_id}/projects"
INVESTIGATOR_URL = "https://reporter.nih.gov/investigator/{profile_id}/projects"

# Fiscal years to include — covers current and prior year of active grants
FISCAL_YEARS = [2024, 2025]

# medicine.umich.edu / Michigan Medicine department type substrings (NIH IMPAC codes)
MEDICINE_DEPTS = {
    "INTERNAL MEDICINE", "SURGERY", "PATHOLOGY", "PHARMACOLOGY", "PEDIATRICS",
    "PSYCHIATRY", "NEUROLOGY", "NEUROSCIENCE", "RADIOLOGY", "ONCOLOGY",
    "ANESTHESIOLOGY", "OBSTETRICS", "GYNECOLOGY", "DERMATOLOGY", "OPHTHALMOLOGY",
    "IMMUNOLOGY", "MICROBIOLOGY", "BIOCHEMISTRY", "BIOPHYSICS", "GENETICS",
    "BIOMEDICAL", "PHYSIOLOGY", "ANATOMY", "EPIDEMIOLOGY", "BIOSTATISTICS",
    "PUBLIC HEALTH", "COMPUTATIONAL", "BIOINFORMATICS", "MOLECULAR", "CELL BIOLOGY",
    "HUMAN GENETICS", "NURSING", "PHARMACY", "DENTAL", "RADIATION",
}


class UMFacultyScraper(BaseScraper):

    def scrape(self) -> list[FacultyData]:
        try:
            results = self._fetch_faculty()
            logger.info(f"UM Faculty: found {len(results)} faculty members")
            return results
        except Exception as e:
            logger.error(f"UM Faculty scraper failed: {e}")
            return []

    def _fetch_faculty(self) -> list[FacultyData]:
        # pi_profile_id → accumulated data dict
        pi_map: dict[int, dict] = defaultdict(lambda: {
            "first_name": "", "last_name": "", "full_name": "", "title": "",
            "dept": "", "terms": set(), "project_titles": []
        })

        offset = 0
        page_size = 500
        total = None

        while total is None or offset < total:
            payload = {
                "criteria": {
                    "org_names": ["UNIVERSITY OF MICHIGAN AT ANN ARBOR"],
                    "fiscal_years": FISCAL_YEARS,
                },
                "offset": offset,
                "limit": page_size,
                "sort_field": "project_start_date",
                "sort_order": "desc",
                "include_fields": [
                    "PrincipalInvestigators",
                    "Organization",
                    "Terms",
                    "ProjectTitle",
                ],
            }

            resp = self.post(API_URL, json=payload)
            data = resp.json()
            meta = data.get("meta", {})

            if total is None:
                total = meta.get("total", 0)
                logger.debug(f"NIH Reporter: {total} U-M projects across fiscal years {FISCAL_YEARS}")

            results = data.get("results", [])
            if not results:
                break

            for project in results:
                org = project.get("organization") or {}
                dept_raw = (org.get("dept_type") or "").upper()

                # Only include Michigan Medicine / health sciences departments
                if not self._is_medicine_dept(dept_raw):
                    continue

                terms_raw = project.get("terms") or ""
                terms = self._parse_terms(terms_raw)
                title = (project.get("project_title") or "").strip()

                for pi in project.get("principal_investigators") or []:
                    pid = pi.get("profile_id")
                    if not pid:
                        continue
                    entry = pi_map[pid]
                    entry["first_name"] = entry["first_name"] or pi.get("first_name", "")
                    entry["last_name"] = entry["last_name"] or pi.get("last_name", "")
                    entry["full_name"] = entry["full_name"] or pi.get("full_name", "")
                    entry["title"] = entry["title"] or pi.get("title", "")
                    entry["dept"] = entry["dept"] or dept_raw.title()
                    entry["terms"].update(terms)
                    if title:
                        entry["project_titles"].append(title)

            offset += page_size
            if offset >= total:
                break

        logger.debug(f"NIH Reporter: {len(pi_map)} unique Michigan Medicine PIs")
        return [self._build_faculty(pid, entry) for pid, entry in pi_map.items()]

    def _build_faculty(self, profile_id: int, entry: dict) -> FacultyData:
        name = entry["full_name"].strip() or f"{entry['first_name']} {entry['last_name']}".strip()
        name = name.title()  # normalize ALL-CAPS names

        # Combine MeSH terms + up to 3 recent project titles as research context
        interests_parts = sorted(entry["terms"])[:30]  # cap at 30 terms
        research_interests = ", ".join(interests_parts)

        profile_url = INVESTIGATOR_URL.format(profile_id=profile_id)

        return FacultyData(
            name=name,
            profile_url=profile_url,
            title=entry["title"].title(),
            department=entry["dept"],
            school="Michigan Medicine",
            research_interests=research_interests,
            raw_data=json.dumps({
                "profile_id": profile_id,
                "source": "nih_reporter",
                "project_count": len(entry["project_titles"]),
            }),
        )

    def _is_medicine_dept(self, dept: str) -> bool:
        if not dept:
            return False
        for keyword in MEDICINE_DEPTS:
            if keyword in dept:
                return True
        return False

    def _parse_terms(self, terms_raw: str) -> set:
        """NIH terms field is a string of <Term> tags: '<Cancer><Drug><Oncology>'"""
        if not terms_raw:
            return set()
        import re
        # Extract text between angle brackets, filter out very short ones
        found = re.findall(r"<([^<>]+)>", terms_raw)
        return {t.strip() for t in found if len(t.strip()) > 3}

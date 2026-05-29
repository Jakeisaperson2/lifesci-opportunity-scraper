"""
U-M Faculty Database Dashboard scraper.
Source: https://tableau.dsc.umich.edu/t/UM-Public/views/FacultyDatabaseDashboard

Downloads Page2 as CSV (plain requests, no JS required — the `:embed=y` parameter
causes Tableau Server to return raw CSV). Parses the three columns:
  - "Faculty Info"                    → NAME / DEPARTMENT / TITLE blocks
  - "Assets, Project Ideas, & Keywords" → LAB ASSETS / CLINICAL ASSETS / PROJECT IDEAS sections
  - "Lab Website"                     → profile / lab URL

Returns list[FacultyData]. Falls back to [] on any error.
"""
import csv
import io
import re
from loguru import logger
from scrapers.base import BaseScraper, FacultyData

CSV_URL = (
    "https://tableau.dsc.umich.edu/t/UM-Public/views"
    "/FacultyDatabaseDashboard/Page2.csv?:showVizHome=no&:embed=y"
)

_SECTION_RE = re.compile(
    r"(LAB ASSETS|CLINICAL ASSETS|PROJECT IDEAS|KEYWORDS)[:\s]*",
    re.IGNORECASE,
)


class TableauFacultyScraper(BaseScraper):

    def scrape(self) -> list[FacultyData]:
        try:
            results = self._fetch()
            logger.info(f"Tableau faculty: found {len(results)} records")
            return results
        except Exception as e:
            logger.error(f"Tableau faculty scraper failed: {e}")
            return []

    def _fetch(self) -> list[FacultyData]:
        resp = self.get(CSV_URL)
        reader = csv.DictReader(io.StringIO(resp.text))
        results = []
        seen_names: set[str] = set()

        for row in reader:
            info_raw = row.get("Faculty Info", "")
            assets_raw = row.get("Assets, Project Ideas, & Keywords", "")
            lab_url = (row.get("Lab Website") or "").strip()

            name, dept, title = self._parse_faculty_info(info_raw)
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            lab_assets, project_ideas = self._parse_assets(assets_raw)

            results.append(FacultyData(
                name=name,
                profile_url=lab_url,
                title=title,
                department=dept,
                school="Michigan Medicine",
                lab_assets=lab_assets,
                project_ideas=project_ideas,
            ))

        return results

    def _parse_faculty_info(self, text: str) -> tuple:
        """Extract (name, department, title) from a Faculty Info cell."""
        name = self._extract_field(text, "NAME")
        dept = self._extract_field(text, "DEPARTMENT")
        title = self._extract_field(text, "TITLE")
        return name.strip(), dept.strip(), title.strip()

    def _extract_field(self, text: str, label: str) -> str:
        """Pull the value after 'LABEL:' up to the next blank line or label."""
        pattern = rf"{label}\s*:\s*(.+?)(?=\n\s*\n|\n[A-Z]+\s*:|$)"
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return ""

    def _parse_assets(self, text: str) -> tuple:
        """
        Split the combined assets/ideas text into (lab_assets, project_ideas).
        Combines LAB ASSETS and CLINICAL ASSETS into lab_assets.
        """
        # Split on section headers
        sections: dict[str, str] = {}
        parts = _SECTION_RE.split(text)

        # parts alternates: [pre-text, header, content, header, content, ...]
        i = 1
        while i + 1 < len(parts):
            header = parts[i].strip().upper()
            content = parts[i + 1].strip()
            sections[header] = content
            i += 2

        lab = "\n\n".join(filter(None, [
            sections.get("LAB ASSETS", ""),
            sections.get("CLINICAL ASSETS", ""),
        ])).strip()

        ideas = sections.get("PROJECT IDEAS", "").strip()

        return lab, ideas

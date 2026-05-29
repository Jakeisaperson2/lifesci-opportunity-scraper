"""
Wellcome Trust grant funding scraper.
Source: https://wellcome.org/grant-funding

The Wellcome Trust is one of the world's largest private biomedical
research funders (~£16B endowment). Their grants span basic science,
clinical research, global health, and humanities of medicine.
Relevant for international collaboration and non-NIH private funding.
"""
import json
import re
from loguru import logger
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, OpportunityData


class WellcomeTrustScraper(BaseScraper):

    BASE_URL = "https://wellcome.org"
    GRANTS_URL = "https://wellcome.org/grant-funding"

    def scrape(self) -> list[OpportunityData]:
        results: list[OpportunityData] = []
        try:
            results = self._fetch_grants()
            logger.info(f"Wellcome Trust: found {len(results)} opportunities")
        except Exception as e:
            logger.error(f"Wellcome Trust scraper failed: {e}")
        return results

    def _fetch_grants(self) -> list[OpportunityData]:
        resp = self.get(self.GRANTS_URL)
        html = resp.text

        # Next.js sites embed all page data as JSON in __NEXT_DATA__
        next_data = self._extract_next_data(html)
        if next_data:
            opportunities = self._parse_next_data(next_data)
            if opportunities:
                return opportunities

        # Fallback: parse rendered HTML for grant cards/links
        return self._parse_html(html)

    def _extract_next_data(self, html: str) -> dict:
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return {}

    def _parse_next_data(self, data: dict) -> list[OpportunityData]:
        """Walk the Next.js page props tree looking for funding opportunity entries."""
        opportunities = []
        try:
            page_props = data.get("props", {}).get("pageProps", {})
            # Try common content shapes Wellcome has used
            entries = (
                page_props.get("grants")
                or page_props.get("fundingOpportunities")
                or page_props.get("opportunities")
                or page_props.get("content", {}).get("grants", [])
                or []
            )
            for entry in entries:
                opp = self._entry_to_opportunity(entry)
                if opp:
                    opportunities.append(opp)
        except Exception as e:
            logger.debug(f"Wellcome Next.js parse error: {e}")
        return opportunities

    def _entry_to_opportunity(self, entry: dict) -> OpportunityData:
        title = (entry.get("title") or entry.get("name") or "").strip()
        if not title:
            return None

        slug = entry.get("slug") or entry.get("url") or ""
        url = slug if slug.startswith("http") else f"{self.BASE_URL}{slug}"
        description = (entry.get("summary") or entry.get("description") or entry.get("intro") or "")[:1000]
        funding = entry.get("fundingAmount") or entry.get("funding_amount") or entry.get("awardRange") or ""
        deadline_str = entry.get("closingDate") or entry.get("deadline") or entry.get("closeDate") or ""
        deadline = self.parse_date(deadline_str, "%Y-%m-%d") or self.parse_date(deadline_str, "%d/%m/%Y")

        return OpportunityData(
            title=title,
            url=url or self.GRANTS_URL,
            description=str(description),
            company_name="Wellcome Trust",
            opportunity_type="grant",
            funding_amount=str(funding) if funding else "",
            deadline=deadline,
            raw_data=json.dumps({"source": "wellcome_next_data", "slug": slug}),
        )

    def _parse_html(self, html: str) -> list[OpportunityData]:
        """Fallback: parse rendered HTML for grant listings."""
        soup = BeautifulSoup(html, "lxml")
        opportunities = []
        seen_urls: set[str] = set()

        # Look for article cards, grant scheme links, or funding call cards
        selectors = [
            "article",
            "[class*='card']",
            "[class*='grant']",
            "[class*='funding']",
            "[class*='opportunity']",
        ]

        candidates = []
        for selector in selectors:
            candidates.extend(soup.select(selector))

        for card in candidates:
            link = card.find("a", href=True)
            if not link:
                continue

            href = link["href"]
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            if url in seen_urls or "grant-funding" not in url:
                continue
            seen_urls.add(url)

            heading = card.find(["h2", "h3", "h4"])
            title = (heading.get_text(strip=True) if heading else link.get_text(strip=True))
            if not title or len(title) < 5:
                continue

            para = card.find("p")
            description = para.get_text(strip=True)[:500] if para else ""

            opportunities.append(OpportunityData(
                title=title,
                url=url,
                description=description,
                company_name="Wellcome Trust",
                opportunity_type="grant",
                raw_data=json.dumps({"source": "wellcome_html", "url": url}),
            ))

        return opportunities

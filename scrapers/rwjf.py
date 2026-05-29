"""
Robert Wood Johnson Foundation (RWJF) funding opportunities scraper.
Source: https://www.rwjf.org/en/grants/funding-opportunities.html

RWJF is the largest US private foundation focused exclusively on health,
with ~$14B endowment. They fund public health, health policy, nursing,
health equity, and population health — often with academic partners.
Relevant as a major non-government, non-pharma health funder.
"""
import json
import re
from loguru import logger
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, OpportunityData


class RWJFScraper(BaseScraper):

    BASE_URL = "https://www.rwjf.org"
    GRANTS_URL = "https://www.rwjf.org/en/grants/funding-opportunities.html"

    # RWJF also exposes a JSON search endpoint used by their SPA
    SEARCH_URL = "https://www.rwjf.org/content/rwjf/en/grants/funding-opportunities.model.json"

    def scrape(self) -> list[OpportunityData]:
        results: list[OpportunityData] = []
        try:
            results = self._fetch_grants()
            logger.info(f"RWJF: found {len(results)} opportunities")
        except Exception as e:
            logger.error(f"RWJF scraper failed: {e}")
        return results

    def _fetch_grants(self) -> list[OpportunityData]:
        # Try the JSON model endpoint first (used by RWJF's internal SPA)
        try:
            resp = self.get(self.SEARCH_URL)
            if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
                data = resp.json()
                opportunities = self._parse_json(data)
                if opportunities:
                    return opportunities
        except Exception as e:
            logger.debug(f"RWJF JSON endpoint failed: {e}")

        # Fallback: scrape rendered HTML
        resp = self.get(self.GRANTS_URL)
        return self._parse_html(resp.text)

    def _parse_json(self, data) -> list[OpportunityData]:
        opportunities = []
        items = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Walk common Adobe Experience Manager / Sitecore JSON shapes
            items = (
                data.get("items")
                or data.get("results")
                or data.get("fundingOpportunities")
                or data.get("grants")
                or []
            )

        for item in items:
            title = (item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            url_path = item.get("url") or item.get("path") or item.get("link") or ""
            url = url_path if url_path.startswith("http") else f"{self.BASE_URL}{url_path}"
            description = (item.get("description") or item.get("summary") or item.get("body") or "")[:1000]
            deadline_str = item.get("deadline") or item.get("closeDate") or item.get("dueDate") or ""
            deadline = self.parse_date(deadline_str, "%Y-%m-%d") or self.parse_date(deadline_str, "%m/%d/%Y")
            funding = item.get("fundingAmount") or item.get("amount") or item.get("awardCeiling") or ""

            opportunities.append(OpportunityData(
                title=title,
                url=url or self.GRANTS_URL,
                description=str(description),
                company_name="Robert Wood Johnson Foundation",
                opportunity_type="grant",
                funding_amount=str(funding) if funding else "",
                deadline=deadline,
                raw_data=json.dumps({"source": "rwjf_json", "path": url_path}),
            ))

        return opportunities

    def _parse_html(self, html: str) -> list[OpportunityData]:
        soup = BeautifulSoup(html, "lxml")
        opportunities = []
        seen_urls: set[str] = set()

        # RWJF listing pages have opportunity cards/rows with links and metadata
        selectors = [
            "article",
            "[class*='card']",
            "[class*='opportunity']",
            "[class*='grant']",
            "li.result",
            "div.result",
        ]

        candidates = []
        for selector in selectors:
            candidates.extend(soup.select(selector))

        # Also check for plain link lists under common funding listing containers
        if not candidates:
            for container in soup.select("main, #main, .content, [role='main']"):
                candidates.extend(container.find_all(["article", "li", "div"], limit=50))

        for card in candidates:
            link = card.find("a", href=True)
            if not link:
                continue

            href = link["href"]
            if "funding-opportunit" not in href and "grants" not in href:
                continue

            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            heading = card.find(["h2", "h3", "h4", "h5"])
            title = (heading.get_text(strip=True) if heading else link.get_text(strip=True)).strip()
            if not title or len(title) < 10:
                continue

            para = card.find("p")
            description = para.get_text(strip=True)[:500] if para else ""

            # Look for a deadline in the card text
            card_text = card.get_text()
            deadline = self._extract_date_from_text(card_text)

            opportunities.append(OpportunityData(
                title=title,
                url=url,
                description=description,
                company_name="Robert Wood Johnson Foundation",
                opportunity_type="grant",
                deadline=deadline,
                raw_data=json.dumps({"source": "rwjf_html", "url": url}),
            ))

        return opportunities

    def _extract_date_from_text(self, text: str):
        """Try to pull a deadline date from free text."""
        patterns = [
            r"(?:deadline|due|closes?|by)\D{0,20}(\w+ \d{1,2},? \d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{2}-\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                for fmt in ("%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
                    parsed = self.parse_date(date_str, fmt)
                    if parsed:
                        return parsed
        return None

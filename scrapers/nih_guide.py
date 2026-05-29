"""
NIH Guide for Grants and Contracts — RSS feed scraper.

The NIH Guide publishes Funding Opportunity Announcements (FOAs) including:
  - RFA (Request for Applications)
  - PAR (Program Announcement with special review)
  - PA  (Program Announcement)
  - RFP (Request for Proposals — NIH contracts)

These are NIH-specific and highly relevant for academic medical centers.
RSS feed: https://grants.nih.gov/feeds/Guide.rss
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from loguru import logger
from scrapers.base import BaseScraper, OpportunityData


class NIHGuideScraper(BaseScraper):
    RSS_URL = "https://grants.nih.gov/feeds/Guide.rss"

    # FOA type prefixes in NIH opportunity numbers
    FOA_TYPE_MAP = {
        "RFA": "rfp",           # Request for Applications — targeted funding
        "RFP": "rfp",           # Request for Proposals — contracts
        "PAR": "grant",         # Program Announcement with special review
        "PA-": "grant",         # Program Announcement
        "OTA": "collaboration", # Other Transaction Authority
        "NOT": None,            # Notices — skip these
    }

    def scrape(self) -> list[OpportunityData]:
        try:
            resp = self.get(self.RSS_URL)
            return self._parse_rss(resp.text)
        except Exception as e:
            logger.error(f"NIH Guide RSS fetch failed: {e}")
            return []

    def _parse_rss(self, xml_text: str) -> list[OpportunityData]:
        opportunities = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"NIH Guide RSS parse error: {e}")
            return []

        channel = root.find("channel")
        if channel is None:
            logger.warning("NIH Guide RSS: no <channel> element found")
            return []

        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date_raw = item.findtext("pubDate")

            if not title or not link:
                continue

            # Skip notices (NOT-XX-XXX) — they aren't funding calls
            opp_type = self._classify_foa_type(title)
            if opp_type is None:
                continue

            pub_date = self._parse_rss_date(pub_date_raw)

            # NIH doesn't include deadline in the RSS item; users follow the link
            opp = OpportunityData(
                title=title,
                url=link,
                description=description[:1000],
                company_name="NIH",
                opportunity_type=opp_type,
                raw_data=json.dumps({"title": title, "link": link, "pubDate": pub_date_raw}),
            )
            opportunities.append(opp)

        logger.info(f"NIH Guide: found {len(opportunities)} opportunities")
        return opportunities

    def _classify_foa_type(self, title: str) -> str | None:
        upper = title.upper()
        for prefix, opp_type in self.FOA_TYPE_MAP.items():
            if prefix in upper:
                return opp_type
        return "grant"  # default for unrecognized NIH announcements

    @staticmethod
    def _parse_rss_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return parsedate_to_datetime(value)
        except Exception:
            return None

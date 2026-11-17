"""
NIH Guide for Grants and Contracts scraper.

The NIH Guide publishes Notices of Funding Opportunity (NOFOs), including:
  - RFA (Request for Applications: targeted, one-time funding)
  - PAR / PAS / PA (Program Announcements)

Primary source: the JSON search API that powers https://grants.nih.gov/funding/searchguide/
It returns every *active* NOFO with structured fields (doc number, institute,
expiration date, purpose). This endpoint is not formally documented, so if it fails
we fall back to the public weekly RSS feed.

Fallback RSS: https://grants.nih.gov/grants/guide/newsfeed/fundingopps.xml
(The old https://grants.nih.gov/feeds/Guide.rss URL now returns 404.)
"""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
from loguru import logger
from scrapers.base import BaseScraper, OpportunityData


class NIHGuideScraper(BaseScraper):
    SEARCH_API_URL = "https://search.grants.nih.gov/guide/api/data"
    RSS_URL = "https://grants.nih.gov/grants/guide/newsfeed/fundingopps.xml"
    GUIDE_BASE = "https://grants.nih.gov/grants/guide"

    PAGE_SIZE = 100
    MAX_RESULTS = 1000  # safety cap; there are typically ~300–500 active NOFOs

    # Document-number prefix → (opportunity_type, guide sub-folder). None type = skip.
    DOC_TYPES = {
        "RFA": ("rfp", "rfa-files"),        # Request for Applications: targeted funding
        "RFP": ("rfp", "rfa-files"),        # Request for Proposals (contracts)
        "PAR": ("grant", "pa-files"),       # Program Announcement, special review
        "PAS": ("grant", "pa-files"),       # Program Announcement, set-aside funds
        "PA": ("grant", "pa-files"),        # Program Announcement
        "OTA": ("collaboration", "rfa-files"),  # Other Transaction Authority
        "NOT": (None, "notice-files"),      # Policy/informational notices: not funding calls
    }

    DOCNUM_RE = re.compile(r"\b(RFA|RFP|PAR|PAS|PA|OTA|NOT)-[A-Z]{2}-\d{2}-\d{3}\b")

    def scrape(self) -> list[OpportunityData]:
        try:
            results = self._scrape_search_api()
            if results:
                logger.info(f"NIH Guide: found {len(results)} active opportunities (search API)")
                return results
            logger.warning("NIH Guide search API returned no results; falling back to RSS")
        except Exception as e:
            logger.warning(f"NIH Guide search API failed ({e}); falling back to RSS")

        try:
            results = self._scrape_rss()
            logger.info(f"NIH Guide: found {len(results)} opportunities (RSS fallback)")
            return results
        except Exception as e:
            logger.error(f"NIH Guide RSS fetch failed: {e}")
            return []

    # ── Primary: search API ────────────────────────────────────────────────

    def _scrape_search_api(self) -> list[OpportunityData]:
        opportunities: list[OpportunityData] = []
        offset = 0
        total = None

        while offset < self.MAX_RESULTS and (total is None or offset < total):
            params = {
                "perpage": self.PAGE_SIZE,
                "from": offset,
                "sort": "reldate:desc",
                "type": "active,activenosis",
                "doctype": "all",
                "query": "",
            }
            resp = self.get(self.SEARCH_API_URL, params=params)
            hits = resp.json().get("data", {}).get("hits", {})
            total = hits.get("total", 0)
            if isinstance(total, dict):  # newer Elasticsearch shape: {"value": n}
                total = total.get("value", 0)

            page = hits.get("hits", [])
            if not page:
                break
            for hit in page:
                opp = self._from_search_record(hit.get("_source", {}))
                if opp:
                    opportunities.append(opp)
            offset += len(page)

        return opportunities

    def _from_search_record(self, rec: dict) -> Optional[OpportunityData]:
        docnum = (rec.get("docnum") or "").strip()
        title = (rec.get("title") or "").strip()
        if not docnum or not title:
            return None

        opp_type, folder = self._doc_type(docnum)
        if opp_type is None:
            return None

        url = self._record_url(rec, docnum, folder)
        if not url:
            return None

        institute = rec.get("primaryIC") or rec.get("parentIC") or "NIH"
        purpose = self._strip_html(rec.get("purpose") or "")
        description = f"{docnum} ({institute}). {purpose}".strip()

        return OpportunityData(
            title=f"{title} [{docnum}]",
            url=url,
            description=description[:1000],
            company_name=f"NIH / {institute}" if institute != "NIH" else "NIH",
            opportunity_type=opp_type,
            deadline=self._parse_iso(rec.get("expdate")),
            raw_data=json.dumps({
                "docnum": docnum,
                "doctype": rec.get("doctype"),
                "institute": institute,
                "activity_codes": rec.get("ac"),
                "release_date": rec.get("reldate"),
                "expiration_date": rec.get("expdate"),
                "clinical_trials": rec.get("clinicaltrials"),
                "grants_gov_id": rec.get("ggid"),
            }),
        )

    def _record_url(self, rec: dict, docnum: str, folder: str) -> Optional[str]:
        # Older NOFOs have an HTML page in the Guide. Newer ones are published only
        # on Grants.gov, so the record has no filename; link there instead. That URL
        # format matches the Grants.gov scraper, so the deduplicator merges the two.
        filename = rec.get("filename")
        if filename:
            return f"{self.GUIDE_BASE}/{folder}/{filename}"
        ggid = rec.get("ggid")
        if ggid:
            return f"https://www.grants.gov/search-results-detail/{ggid}"
        return None

    # ── Fallback: weekly RSS feed ──────────────────────────────────────────

    def _scrape_rss(self) -> list[OpportunityData]:
        resp = self.get(self.RSS_URL)
        root = ET.fromstring(resp.content)  # bytes, so the XML's declared encoding is honored
        channel = root.find("channel")
        if channel is None:
            logger.warning("NIH Guide RSS: no <channel> element found")
            return []

        opportunities = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip().replace("http://", "https://", 1)
            description = (item.findtext("description") or "").strip()
            if not title or not link:
                continue

            # The doc number appears in the link filename and description, not the title
            match = self.DOCNUM_RE.search(f"{link} {description}".upper())
            docnum = match.group(0) if match else ""
            opp_type, _ = self._doc_type(docnum) if docnum else ("grant", None)
            if opp_type is None:
                continue

            opportunities.append(OpportunityData(
                title=f"{title} [{docnum}]" if docnum else title,
                url=link,
                description=description[:1000],
                company_name="NIH",
                opportunity_type=opp_type,
                raw_data=json.dumps({"docnum": docnum, "link": link, "pubDate": item.findtext("pubDate")}),
            ))
        return opportunities

    # ── Helpers ────────────────────────────────────────────────────────────

    def _doc_type(self, docnum: str) -> tuple:
        prefix = docnum.split("-", 1)[0].upper()
        return self.DOC_TYPES.get(prefix, ("grant", "pa-files"))

    @staticmethod
    def _strip_html(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", html.unescape(text)).strip()

    @staticmethod
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None

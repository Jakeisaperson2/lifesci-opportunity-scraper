"""
Deduplication logic.

Primary key: MD5 hash of the normalized URL (lowercased, stripped, no trailing slash).
Secondary check: normalized title match within the same source — catches cases where
a source changes its URL structure but the opportunity is the same.
"""
import hashlib
import re
from scrapers.base import OpportunityData


def normalize_url(url: str) -> str:
    return url.strip().lower().rstrip("/")


def url_hash(url: str) -> str:
    return hashlib.md5(normalize_url(url).encode()).hexdigest()


def normalize_title(title: str) -> str:
    # Remove punctuation, collapse whitespace, lowercase
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def is_duplicate(opp: OpportunityData, db) -> bool:
    """
    Check if an equivalent opportunity already exists in the database.
    Returns True if a duplicate is found (skip this record).
    """
    from database.models import Opportunity

    h = url_hash(opp.url)
    exists = db.query(Opportunity).filter(Opportunity.url_hash == h).first()
    return exists is not None


def prepare_hashes(opp: OpportunityData) -> tuple[str, str]:
    """Return (url_hash, title_normalized) ready to write to the DB row."""
    return url_hash(opp.url), normalize_title(opp.title)

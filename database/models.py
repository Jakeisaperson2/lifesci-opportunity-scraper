from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SourceSite(Base):
    """A configured website or API endpoint to scrape."""
    __tablename__ = "source_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    scraper_key = Column(String(100), nullable=False)  # maps to a class in scrapers/registry.py
    enabled = Column(Boolean, default=True)
    last_scraped = Column(DateTime, nullable=True)
    scrape_interval_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    opportunities = relationship("Opportunity", back_populates="source")
    scrape_runs = relationship("ScrapeRun", back_populates="source", cascade="all, delete-orphan")


class Opportunity(Base):
    """A single discovered funding or collaboration opportunity."""
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    title_normalized = Column(String(500), index=True)   # lowercased + stripped, used for dedup
    description = Column(Text)
    company_name = Column(String(255))
    opportunity_type = Column(String(100), index=True)   # grant, clinical_trial, rfp, collaboration
    therapeutic_area = Column(String(255), index=True)
    funding_amount = Column(String(100))
    deadline = Column(DateTime, nullable=True)
    url = Column(String(1000), unique=True, index=True)
    url_hash = Column(String(64), unique=True, index=True)  # MD5 of normalized URL, primary dedup key
    contact_info = Column(Text)
    date_discovered = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_site_id = Column(Integer, ForeignKey("source_sites.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    raw_data = Column(Text)  # JSON blob of the original API response

    source = relationship("SourceSite", back_populates="opportunities")


class FacultyMember(Base):
    """A research faculty member scraped from the Michigan Medicine directory."""
    __tablename__ = "faculty_members"

    id                 = Column(Integer, primary_key=True, index=True)
    name               = Column(String(255), nullable=False)
    title              = Column(String(255))
    department         = Column(String(255), index=True)
    school             = Column(String(255))
    research_interests = Column(Text)
    lab_assets         = Column(Text)
    project_ideas      = Column(Text)
    email              = Column(String(255))
    phone              = Column(String(100))
    profile_url        = Column(String(1000), unique=True, index=True)
    url_hash           = Column(String(64), unique=True, index=True)
    date_discovered    = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    last_updated       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active          = Column(Boolean, default=True)
    raw_data           = Column(Text)


class ScrapeRun(Base):
    """A record of one execution of a scraper against a source site."""
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_site_id = Column(Integer, ForeignKey("source_sites.id"), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running, success, failed
    opportunities_found = Column(Integer, default=0)
    opportunities_new = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    source = relationship("SourceSite", back_populates="scrape_runs")

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SourceSite(Base):
    __tablename__ = "source_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    scraper_key = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    last_scraped = Column(DateTime, nullable=True)
    scrape_interval_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    opportunities = relationship("Opportunity", back_populates="source")
    scrape_runs = relationship("ScrapeRun", back_populates="source", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    org_type = Column(String(100))   # pharma, biotech, academic, government, nonprofit, other
    website = Column(String(1000))
    notes = Column(Text)
    relationship_status = Column(String(100), default="prospect")  # prospect, active, partner, inactive
    last_contact_date = Column(DateTime, nullable=True)
    next_followup_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    contacts = relationship("Contact", back_populates="organization")
    opportunities = relationship("Opportunity", back_populates="organization")
    activities = relationship("Activity", back_populates="organization")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    email = Column(String(255))
    phone = Column(String(100))
    linkedin = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="contacts")
    activities = relationship("Activity", back_populates="contact")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    title_normalized = Column(String(500), index=True)
    description = Column(Text)
    company_name = Column(String(255))
    opportunity_type = Column(String(100), index=True)
    therapeutic_area = Column(String(255), index=True)
    funding_amount = Column(String(100))
    deadline = Column(DateTime, nullable=True)
    url = Column(String(1000), unique=True, index=True)
    url_hash = Column(String(64), unique=True, index=True)
    contact_info = Column(Text)
    date_discovered = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_site_id = Column(Integer, ForeignKey("source_sites.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    raw_data = Column(Text)
    crm_status = Column(String(100), default="new", index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    source = relationship("SourceSite", back_populates="opportunities")
    organization = relationship("Organization", back_populates="opportunities")
    activities = relationship("Activity", back_populates="opportunity")
    tasks = relationship("Task", back_populates="opportunity")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    activity_type = Column(String(100))  # email, meeting, phone_call, proposal_submission, follow_up, internal_review, negotiation
    description = Column(Text)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    opportunity = relationship("Opportunity", back_populates="activities")
    organization = relationship("Organization", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(500), nullable=False)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String(50), default="medium")  # low, medium, high, urgent
    assigned_to = Column(String(255))
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    status = Column(String(50), default="open", index=True)  # open, in_progress, complete
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    opportunity = relationship("Opportunity", back_populates="tasks")


class FacultyMember(Base):
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

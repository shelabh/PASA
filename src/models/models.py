from sqlalchemy import Column, String, DateTime, Text, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base


class JobPost(Base):
    __tablename__ = "job_posts"

    job_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    sender = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    # Enrichment fields
    links = Column(Text, nullable=True)   # comma-separated list of links
    emails = Column(Text, nullable=True)  # comma-separated list of emails
    company_id = Column(String, ForeignKey("companies.company_id"), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="job_posts")

    def __repr__(self):
        return f"<JobPost(job_id={self.job_id}, sender={self.sender})>"


class UserProfile(Base):
    __tablename__ = "user_profile"

    user_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    github = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    twitter = Column(String, nullable=True)

    resume_link = Column(Text, nullable=True)
    # Rich profile context used to tailor applications
    profile_context = Column(Text, nullable=True)
    # Store resume contents to allow attaching to outgoing emails
    resume_bytes = Column(LargeBinary, nullable=True)
    resume_filename = Column(String, nullable=True)
    resume_mime = Column(String, nullable=True)

    # New: save user’s past work/project/company links for enrichment
    past_work_links = Column(Text, nullable=True)  # comma-separated list of URLs

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, name={self.name})>"


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    twitter = Column(String, nullable=True)

    # Context generated from scraping Firecrawl or other enrichment
    company_context = Column(Text, nullable=True)

    # Relationships
    job_posts = relationship("JobPost", back_populates="company")

    def __repr__(self):
        return f"<Company(company_id={self.company_id}, name={self.name})>"

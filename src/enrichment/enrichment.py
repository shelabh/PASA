# src/enrichment/enrichment.py
import io
import json
import os
from typing import List
from sqlalchemy.orm import Session
from pypdf import PdfReader

from src.models.models import UserProfile, Company
from src.enrichment.scraper import scrape_url
from src.enrichment.llm import analyze_content

MAX_RESUME_CHARS = int(os.getenv("MAX_RESUME_CHARS", "12000"))


def _read_resume_bytes(resume_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(resume_bytes))
        pages = []
        for p in reader.pages:
            try:
                t = p.extract_text()
                if t:
                    pages.append(t)
            except Exception:
                continue
        return "\n".join(pages)[:MAX_RESUME_CHARS]
    except Exception:
        return ""


def _collect_user_sources(user: UserProfile) -> List[str]:
    sources = []
    if user.resume_bytes:
        txt = _read_resume_bytes(user.resume_bytes)
        if txt:
            sources.append(f"[resume]\n{txt}")

    if user.resume_link:
        scraped = scrape_url(user.resume_link)
        if scraped:
            sources.append(f"[resume_link] {scraped}")

    for handle in (user.github, user.linkedin, user.twitter):
        if handle:
            scraped = scrape_url(handle)
            if scraped:
                sources.append(f"[social:{handle}] {scraped}")

    if user.past_work_links:
        for link in [l.strip() for l in user.past_work_links.split(",") if l.strip()]:
            scraped = scrape_url(link)
            if scraped:
                sources.append(f"[past_work:{link}] {scraped}")

    return sources


def _collect_company_sources(company: Company) -> List[str]:
    sources = []
    if company.website:
        scraped = scrape_url(company.website)
        if scraped:
            sources.append(f"[website:{company.website}] {scraped}")

    for handle in (company.linkedin, company.twitter):
        if handle:
            scraped = scrape_url(handle)
            if scraped:
                sources.append(f"[social:{handle}] {scraped}")

    return sources


def enrich_user_profile(db: Session, user_id: str) -> str:
    """
    Enriches the UserProfile.profile_context with a JSON string created by the LLM.
    Returns the JSON string stored (or empty string on failure).
    """
    user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not user:
        raise ValueError(f"user {user_id} not found")

    sources = _collect_user_sources(user)
    if not sources:
        # nothing to analyze
        return user.profile_context or ""

    combined = "\n\n".join(sources)
    result_json = analyze_content(combined, context_type="user")

    # Save JSON string
    user.profile_context = result_json
    db.add(user)
    db.commit()
    db.refresh(user)
    return result_json


def enrich_company(db: Session, company_id: str) -> str:
    """
    Enriches the Company.company_context with a JSON string created by the LLM.
    Returns the JSON string stored (or empty string on failure).
    """
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise ValueError(f"company {company_id} not found")

    sources = _collect_company_sources(company)
    if not sources:
        return company.company_context or ""

    combined = "\n\n".join(sources)
    result_json = analyze_content(combined, context_type="company")

    company.company_context = result_json
    db.add(company)
    db.commit()
    db.refresh(company)
    return result_json

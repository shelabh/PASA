# src/db/crud.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models.models import JobPost, UserProfile, Company

# JobPost CRUD
def create_job_post(session: Session, job: JobPost) -> JobPost:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def get_job_posts(session: Session, company: Optional[str] = None, limit: int = 100) -> List[JobPost]:
    query = select(JobPost)
    if company:
        query = query.where(JobPost.company_id == company)
    return session.execute(query.limit(limit)).scalars().all()

# UserProfile CRUD
def create_user_profile(session: Session, profile: UserProfile) -> UserProfile:
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile

def get_user_profile(session: Session, user_id: str) -> Optional[UserProfile]:
    return session.execute(select(UserProfile).where(UserProfile.user_id == user_id)).scalar_one_or_none()

# Company CRUD
def create_company(session: Session, company: Company) -> Company:
    session.add(company)
    session.commit()
    session.refresh(company)
    return company

def get_companies(session: Session, limit: int = 100) -> List[Company]:
    return session.execute(select(Company).limit(limit)).scalars().all()

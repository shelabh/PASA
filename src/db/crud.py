# src/db/crud.py
from typing import List, Optional
from sqlmodel import select, Session
from src.models.models import WhatsAppMessage, JobPosting

# WhatsAppMessage CRUD
def create_message(session: Session, message: WhatsAppMessage) -> WhatsAppMessage:
    session.add(message)
    session.commit()
    session.refresh(message)
    return message

def get_messages(session: Session, limit: int = 100) -> List[WhatsAppMessage]:
    return session.exec(select(WhatsAppMessage).limit(limit)).all()


# JobPosting CRUD
def create_job_posting(session: Session, job: JobPosting) -> JobPosting:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def get_job_postings(session: Session, company: Optional[str] = None, limit: int = 100) -> List[JobPosting]:
    query = select(JobPosting)
    if company:
        query = query.where(JobPosting.company_name == company)
    return session.exec(query.limit(limit)).all()

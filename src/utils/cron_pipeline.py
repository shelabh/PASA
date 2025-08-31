# src/pipeline/cron_pipeline.py
import os
import time
from sqlalchemy.orm import Session
from src.db.database import SessionLocal
from src.models.models import UserProfile, Company
from src.enrichment.enrichment import enrich_user_profile, enrich_company

def run_enrichment_once():
    db: Session = SessionLocal()
    try:
        users = db.query(UserProfile).all()
        for u in users:
            try:
                print(f"[enrich] user: {u.user_id} ({u.name})")
                enrich_user_profile(db, u.user_id)
            except Exception as e:
                print(f"[enrich] failed user {u.user_id}: {e}")

        companies = db.query(Company).all()
        for c in companies:
            try:
                print(f"[enrich] company: {c.company_id} ({c.name})")
                enrich_company(db, c.company_id)
            except Exception as e:
                print(f"[enrich] failed company {c.company_id}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Simple runner for cron: executes once per invocation.
    # Cron should call this script (e.g., every 6 hours).
    run_enrichment_once()

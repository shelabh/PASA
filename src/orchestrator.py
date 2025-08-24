# src/pasa/orchestrator.py
from datetime import datetime
from src.ingestion.whatsapp_parser import parse_whatsapp_chat
from src.nlp.job_detector import is_job_post
from src.db.database import SessionLocal, engine
from src.models.models import Base, JobPost

def main():
    Base.metadata.create_all(bind=engine)

    messages = parse_whatsapp_chat("data/whatsapp/group.txt")
    session = SessionLocal()
    for m in messages:
        if is_job_post(m["message"]):
            job_id = f"{m['timestamp']}_{m['sender']}"
            job = JobPost(job_id=job_id,
                          timestamp=datetime.fromisoformat(m["timestamp"]),
                          sender=m["sender"],
                          message=m["message"])
            session.merge(job)
    session.commit()
    session.close()

if __name__ == "__main__":
    main()

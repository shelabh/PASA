# src/pasa/orchestrator.py
from src.ingestion.whatsapp_parser import parse_whatsapp_chat
from src.nlp.job_detector import JobDetector
from src.db.database import SessionLocal, engine
from src.models.models import Base, JobPost
from src.enrichment.page_fetcher import fetch_text
from src.actions.email_sender import send_email
from src.actions.form_filler import fill_google_form
from src.embeddings.matcher import compute_similarity


def main():
    print("🚀 Starting Orchestrator Pipeline...")
    detector = JobDetector()

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("🗄️ Database tables checked/created.")

    # Parse messages
    msgs = parse_whatsapp_chat("data/whatsapp/group.txt")
    print(f"📥 Parsed {len(msgs)} messages from WhatsApp export.")

    session = SessionLocal()
    job_count = 0

    for m in msgs:
        print(f"\n🔍 Checking message from {m['sender']} at {m['timestamp'][:19]}...")

        job_info = detector.parse_job(m["message"])  # returns {links, emails} or None

        if job_info:
            print("✅ Classified as JOB POST.")
            job_count += 1

            links = job_info.get("links", [])
            emails = job_info.get("emails", [])

            job = JobPost(
                job_id=f"{m['timestamp']}_{m['sender']}",
                timestamp=m["timestamp"],
                sender=m["sender"],
                message=m["message"],
                links=",".join(links) if links else None,
                emails=",".join(emails) if emails else None,
            )
            session.merge(job)

            # 🔗 Enrichment
            if links:
                for link in links:
                    print(f"🌐 Fetching job details from link: {link}")
                    job_text = fetch_text(link)
                    score = compute_similarity(job_text, "YOUR PROFILE TEXT")
                    print(f"📊 Job relevance score: {score:.2f}")
            else:
                print("⚠️ No job links found, skipping enrichment.")

            # 📧 / 📝 Actions
            if emails:
                for email in emails:
                    print(f"📧 Sending application email to {email}")
                    send_email(email, f"Applying: {getattr(job, 'title', 'Job')}", "Email body here")
            elif m.get("form_url"):
                print(f"📝 Filling Google Form: {m['form_url']}")
                field_map = {"Your Name": "Your Name", "Email": "your@email.com"}
                fill_google_form(m["form_url"], field_map)
        else:
            print("❌ Not a job post.")

    session.commit()
    session.close()
    print(f"\n🎯 Pipeline finished. Total job posts detected: {job_count}")


if __name__ == "__main__":
    main()

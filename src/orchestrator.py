# src/pasa/orchestrator.py
from src.ingestion.whatsapp_parser import parse_whatsapp_chat
from src.nlp.job_detector import JobDetector
from src.db.database import SessionLocal, engine
from src.models.models import Base, JobPost, UserProfile
from src.enrichment.page_fetcher import fetch_text
from src.actions.email_sender import send_email
from src.actions.form_filler import fill_google_form
from src.embeddings.matcher import compute_similarity
import os
import mimetypes
from src.nlp.email_writer import generate_email_subject_body


def upsert_user_profile(session: "SessionLocal") -> UserProfile:
    """Upsert a single user's profile from environment variables and optional resume file.

    Expected environment variables:
    - USER_ID, USER_NAME, USER_EMAIL
    - USER_GITHUB, USER_LINKEDIN, USER_TWITTER (optional)
    - USER_PROFILE_CONTEXT (optional)
    - USER_RESUME_PATH (optional path to a PDF or DOCX)
    """
    user_id = os.getenv("USER_ID", "default_user")
    name = os.getenv("USER_NAME", "Your Name")
    email = os.getenv("USER_EMAIL", "your@email.com")
    github = os.getenv("USER_GITHUB")
    linkedin = os.getenv("USER_LINKEDIN")
    twitter = os.getenv("USER_TWITTER")
    profile_context = os.getenv("USER_PROFILE_CONTEXT")
    resume_path = os.getenv("USER_RESUME_PATH")

    resume_bytes = None
    resume_filename = None
    resume_mime = None
    if resume_path and os.path.isfile(resume_path):
        with open(resume_path, "rb") as f:
            resume_bytes = f.read()
        resume_filename = os.path.basename(resume_path)
        guessed, _ = mimetypes.guess_type(resume_path)
        resume_mime = guessed or "application/octet-stream"

    existing: UserProfile | None = session.get(UserProfile, user_id)
    if existing:
        existing.name = name
        existing.email = email
        existing.github = github
        existing.linkedin = linkedin
        existing.twitter = twitter
        existing.profile_context = profile_context
        # Only update resume fields if provided
        if resume_bytes is not None:
            existing.resume_bytes = resume_bytes
            existing.resume_filename = resume_filename
            existing.resume_mime = resume_mime
        session.add(existing)
        return existing
    profile = UserProfile(
        user_id=user_id,
        name=name,
        email=email,
        github=github,
        linkedin=linkedin,
        twitter=twitter,
        profile_context=profile_context,
        resume_bytes=resume_bytes,
        resume_filename=resume_filename,
        resume_mime=resume_mime,
    )
    session.add(profile)
    return profile


def build_curated_email(job: JobPost, profile: UserProfile, link_sample: str | None) -> tuple[str, str]:
    """Return subject and body tailored to the job using profile context and message.

    link_sample is a representative link (if any) to mention in the email.
    """
    job_title = getattr(job, "title", None) or "Application"
    subject = f"{job_title} – {profile.name}"

    summary = job.message[:600] + ("…" if len(job.message) > 600 else "")
    lines = [
        f"Hi Hiring Team,",
        "",
        f"I'm {profile.name} and I'm excited to apply.",
        "",
        "Why me:",
    ]
    if profile.profile_context:
        lines.append(profile.profile_context)
    else:
        lines.append("- Relevant experience and strong interest in this role.")
    lines.extend([
        "",
        "Job context I saw:",
        summary,
    ])
    if link_sample:
        lines.extend(["", f"Reference link: {link_sample}"])
    lines.extend([
        "",
        "I've attached my resume. Happy to share more details.",
        f"LinkedIn: {profile.linkedin or 'N/A'}",
        f"GitHub: {profile.github or 'N/A'}",
        "",
        "Best regards,",
        profile.name,
        profile.email,
    ])
    body = "\n".join(lines)
    return subject, body


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

    # Upsert user profile once before processing
    profile = upsert_user_profile(session)
    session.commit()

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
                    score = compute_similarity(job_text, profile.profile_context or "")
                    print(f"📊 Job relevance score: {score:.2f}")
            else:
                print("⚠️ No job links found, skipping enrichment.")

            # 📧 / 📝 Actions
            if emails:
                for email in emails:
                    print(f"📧 Sending application email to {email}")
                    # Build LLM-curated email via Groq
                    first_link = links[0] if links else None
                    subject, body = generate_email_subject_body(
                        profile_name=profile.name,
                        profile_email=profile.email,
                        profile_context=profile.profile_context,
                        job_summary=job.message,
                        job_link=first_link,
                    )
                    # Prepare resume attachment if present in DB
                    attachments = None
                    if profile.resume_bytes and profile.resume_filename:
                        attachments = [(profile.resume_filename, profile.resume_bytes, profile.resume_mime or "application/octet-stream")]
                    send_email(email, subject, body, attachments=attachments)
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

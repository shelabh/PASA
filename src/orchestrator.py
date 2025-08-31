# src/pasa/orchestrator.py
from src.ingestion.whatsapp_parser import parse_whatsapp_chat
from src.nlp.job_detector import JobDetector
from src.db.database import SessionLocal, engine
from src.models.models import Base, JobPost, UserProfile, Company
from src.enrichment.scraper import scrape_url
from src.enrichment.enrichment import enrich_user_profile, enrich_company
from src.actions.email_sender import send_email
from src.actions.form_filler import fill_google_form
from src.embeddings.matcher import compute_similarity
import os
import mimetypes
import logging
from datetime import datetime
from src.nlp.email_writer import generate_email_subject_body
from src.nlp.job_fit import evaluate_job_fit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pasa_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
    logger.info("🚀 ===== STARTING PASA PIPELINE =====")
    logger.info(f"Pipeline started at: {datetime.now().isoformat()}")
    
    detector = JobDetector()
    logger.info("✅ JobDetector initialized")

    # Ensure tables exist
    logger.info("🗄️ Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready")

    # Parse messages
    logger.info("📥 Parsing WhatsApp chat messages...")
    msgs = parse_whatsapp_chat("data/whatsapp/group.txt")
    logger.info(f"✅ Parsed {len(msgs)} messages from WhatsApp export")

    session = SessionLocal()
    job_count = 0
    applied_count = 0
    skipped_count = 0

    # Upsert user profile once before processing
    logger.info("👤 Setting up user profile...")
    profile = upsert_user_profile(session)
    session.commit()
    logger.info(f"✅ User profile ready: {profile.name} ({profile.user_id})")

    # Step 1: Enrich user profile if not already enriched
    logger.info("🔍 STEP 1: User Profile Enrichment")
    if not profile.profile_context:
        logger.info("📋 User profile not enriched yet, starting enrichment process...")
        try:
            logger.info("🔄 Calling enrich_user_profile()...")
            enrich_user_profile(session, profile.user_id)
            session.refresh(profile)
            logger.info("✅ User profile enriched successfully")
        except Exception as e:
            logger.error(f"❌ Failed to enrich user profile: {e}")
    else:
        logger.info("✅ User profile already enriched, skipping enrichment step")

    logger.info(f"🔄 Starting to process {len(msgs)} messages...")
    
    for i, m in enumerate(msgs, 1):
        logger.info(f"\n📝 MESSAGE {i}/{len(msgs)}: Processing message from {m['sender']} at {m['timestamp'][:19]}")
        logger.info(f"📄 Message preview: {m['message'][:100]}{'...' if len(m['message']) > 100 else ''}")

        # Step 2: Job Detection
        logger.info("🔍 STEP 2: Job Detection")
        job_info = detector.parse_job(m["message"])  # returns {links, emails} or None

        if job_info:
            logger.info("✅ MESSAGE CLASSIFIED AS JOB POST")
            job_count += 1
            logger.info(f"📊 Job info extracted: {list(job_info.keys())}")

            links = job_info.get("links", [])
            emails = job_info.get("emails", [])
            company_name = job_info.get("company")
            
            logger.info(f"🔗 Links found: {len(links)}")
            logger.info(f"📧 Emails found: {len(emails)}")
            logger.info(f"🏢 Company: {company_name or 'Not specified'}")

            # Create or get company record
            company = None
            if company_name:
                logger.info(f"🏢 Looking up company: {company_name}")
                company = session.query(Company).filter(Company.name == company_name).first()
                if not company:
                    logger.info(f"🏢 Creating new company record: {company_name}")
                    company = Company(
                        company_id=f"company_{company_name.lower().replace(' ', '_')}",
                        name=company_name
                    )
                    session.add(company)
                    session.commit()
                    logger.info(f"✅ Company created: {company.company_id}")
                else:
                    logger.info(f"✅ Company found: {company.company_id}")
            else:
                logger.info("⚠️ No company name found in job info")

            logger.info("💾 Creating job post record...")
            job = JobPost(
                job_id=f"{m['timestamp']}_{m['sender']}",
                timestamp=m["timestamp"],
                sender=m["sender"],
                message=m["message"],
                links=",".join(links) if links else None,
                emails=",".join(emails) if emails else None,
                company_id=company.company_id if company else None,
            )
            session.merge(job)
            logger.info(f"✅ Job post saved: {job.job_id}")

            # Step 3: Scraping & Enrichment
            logger.info("🌐 STEP 3: Scraping & Enrichment")
            job_description = m["message"]  # Start with original message
            logger.info(f"📄 Original message length: {len(job_description)} characters")
            
            if links:
                logger.info(f"🌐 Scraping job details from {len(links)} link(s)...")
                scraped_texts = []
                for i, link in enumerate(links, 1):
                    logger.info(f"🔗 Scraping link {i}/{len(links)}: {link}")
                    try:
                        scraped_text = scrape_url(link)
                        if scraped_text:
                            scraped_texts.append(scraped_text)
                            logger.info(f"✅ Successfully scraped: {len(scraped_text)} characters from {link[:50]}...")
                        else:
                            logger.warning(f"⚠️ No content scraped from {link}")
                    except Exception as e:
                        logger.error(f"❌ Failed to scrape {link}: {e}")
                
                if scraped_texts:
                    job_description = m["message"] + "\n\n" + "\n\n".join(scraped_texts)
                    logger.info(f"📄 Combined job description length: {len(job_description)} characters")
                else:
                    logger.warning("⚠️ No content was successfully scraped from any links")
            else:
                logger.info("⚠️ No links found, using original message only")

            # Step 4: Company Enrichment (if company exists and not enriched)
            logger.info("🏢 STEP 4: Company Enrichment")
            if company and not company.company_context:
                logger.info(f"🏢 Enriching company profile: {company.name}")
                try:
                    logger.info("🔄 Calling enrich_company()...")
                    enrich_company(session, company.company_id)
                    session.refresh(company)
                    logger.info("✅ Company profile enriched successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to enrich company profile: {e}")
            elif company and company.company_context:
                logger.info("✅ Company profile already enriched, skipping enrichment")
            else:
                logger.info("⚠️ No company to enrich (no company found or no company name)")

            # Step 5: Job Fit Analysis
            logger.info("🎯 STEP 5: Job Fit Analysis")
            logger.info("🔄 Calling evaluate_job_fit()...")
            try:
                fit_analysis = evaluate_job_fit(
                    profile_context=profile.profile_context or "",
                    job_description=job_description
                )
                
                fit_score = fit_analysis.get("score", 0)
                fit_chance = fit_analysis.get("chance", "low")
                fit_reason = fit_analysis.get("reason", "")
                match_highlights = fit_analysis.get("match_highlights", [])
                email_style = fit_analysis.get("recommended_email_style", "brief")
                
                logger.info(f"📊 Job Fit Score: {fit_score}/100")
                logger.info(f"🎯 Likelihood: {fit_chance}")
                logger.info(f"💡 Reasoning: {fit_reason}")
                logger.info(f"🎨 Recommended email style: {email_style}")
                if match_highlights:
                    logger.info(f"✨ Match highlights: {', '.join(match_highlights[:3])}{'...' if len(match_highlights) > 3 else ''}")
                
                # Only proceed if fit is reasonable (score >= 30 or chance is medium/high)
                should_apply = fit_score >= 30 or fit_chance in ["medium", "high"]
                
                if should_apply:
                    logger.info("✅ Job fit analysis PASSED - proceeding with application")
                else:
                    logger.info("❌ Job fit analysis FAILED - skipping application")
                    skipped_count += 1
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Failed to analyze job fit: {e}")
                logger.info("⚠️ Continuing with application due to fit analysis failure")
                # Continue with application if fit analysis fails
                should_apply = True

            # Step 6: Email Writing & Sending
            logger.info("📧 STEP 6: Email Writing & Sending")
            if emails and should_apply:
                logger.info(f"📧 Found {len(emails)} email(s) to send applications to")
                for i, email in enumerate(emails, 1):
                    logger.info(f"📧 Sending application {i}/{len(emails)} to {email}")
                    try:
                        # Build LLM-curated email via Groq
                        logger.info("🔄 Generating email content...")
                        first_link = links[0] if links else None
                        subject, body = generate_email_subject_body(
                            profile_name=profile.name,
                            profile_email=profile.email,
                            profile_context=profile.profile_context,
                            job_summary=job.message,
                            job_link=first_link,
                        )
                        
                        logger.info(f"📝 Email generated - Subject: {subject[:50]}{'...' if len(subject) > 50 else ''}")
                        logger.info(f"📄 Email body length: {len(body)} characters")
                        
                        # Prepare resume attachment if present in DB
                        attachments = None
                        if profile.resume_bytes and profile.resume_filename:
                            attachments = [(profile.resume_filename, profile.resume_bytes, profile.resume_mime or "application/octet-stream")]
                            logger.info(f"📎 Resume attachment prepared: {profile.resume_filename}")
                        else:
                            logger.info("⚠️ No resume attachment available")
                        
                        logger.info("🔄 Sending email...")
                        send_email(email, subject, body, attachments=attachments)
                        applied_count += 1
                        logger.info(f"✅ Application sent successfully to {email}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to send application to {email}: {e}")
                        
            elif m.get("form_url") and should_apply:
                logger.info(f"📝 Filling Google Form: {m['form_url']}")
                try:
                    field_map = {"Your Name": profile.name, "Email": profile.email}
                    logger.info(f"📝 Form fields: {field_map}")
                    fill_google_form(m["form_url"], field_map)
                    applied_count += 1
                    logger.info("✅ Google Form filled successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to fill Google Form: {e}")
            else:
                logger.warning("⚠️ No application method found (no emails or form URL)")
                skipped_count += 1
        else:
            logger.info("❌ MESSAGE NOT CLASSIFIED AS JOB POST - skipping")

    session.commit()
    session.close()
    
    logger.info("🏁 ===== PIPELINE COMPLETED =====")
    logger.info(f"📊 Final Statistics:")
    logger.info(f"   • Total messages processed: {len(msgs)}")
    logger.info(f"   • Job posts detected: {job_count}")
    logger.info(f"   • Applications sent: {applied_count}")
    logger.info(f"   • Jobs skipped (low fit/no method): {skipped_count}")
    logger.info(f"Pipeline completed at: {datetime.now().isoformat()}")
    
    print(f"\n🎯 Pipeline finished. Total job posts detected: {job_count}, Applications sent: {applied_count}, Skipped: {skipped_count}")


if __name__ == "__main__":
    main()

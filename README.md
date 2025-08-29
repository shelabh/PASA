# PASA - Personal Autonomous Software Assistant (MVP)

## Setup (local dev)

```bash
git clone <repo-url>
cd pasa
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Set these before running. You can export in your shell or place them in a `.env` file.

```bash
# Database
DATABASE_URL="postgresql+psycopg2://user:pass@host/db"

# Email (SMTP)
EMAIL_ADDRESS="youremail@gmail.com"
 EMAIL_PASSWORD="your-app-password"   # use an app password
 SMTP_SERVER="smtp.gmail.com"
 SMTP_PORT="587"

# User profile (stored in DB and used for applications)
 USER_ID="john"                    # any stable identifier
 USER_NAME="john doe"
 USER_EMAIL="john@example.com"
 USER_GITHUB=""      # optional
 USER_LINKEDIN="" # optional
 USER_TWITTER=""                          # optional
 USER_PROFILE_CONTEXT="- 5y Python/LLMs\n- Built data pipelines (example)"  # short paragraph or bullets
 USER_RESUME_PATH="/absolute/path/to/resume.pdf"  # e.g., /Users/you/path/PASA/data/resume/Your_Resume.pdf

# LLM (Groq OpenAI-compatible API)
 GROQ_API_KEY="your_groq_key"
 GROQ_BASE_URL="https://api.groq.com/openai/v1"   # default
 GROQ_MODEL="llama-3.3-70b-versatile"

# Data source
 WHATSAPP_EXPORT_PATH="data/whatsapp/group.txt"
```

## Database migrations

Use Alembic to apply schema updates:

```bash
alembic upgrade head
```

Notes:
- Creating new tables is handled at runtime, but altering existing tables requires migrations.
- If you added new columns and see errors like `UndefinedColumn`, ensure you ran `alembic upgrade head`.

## Run the pipeline

```bash
python -m src.orchestrator
```

What happens:
- User profile is upserted from env vars into the DB (including reading and storing resume bytes, filename, and mime type if `USER_RESUME_PATH` is set).
- WhatsApp export is parsed, potential job posts are detected, and posts are stored.
- Optional enrichment fetches job page text and computes a simple relevance score to your profile context.
- For posts with emails, an LLM (Groq) generates a tailored subject/body and an email is sent with your stored resume attached.
- If a Google Form is present (experimental), it attempts to auto-fill.

## MVP

The current MVP includes:
- WhatsApp ingestion: parse `data/whatsapp/group.txt` into structured messages.
- NLP job detector: identify likely job posts and extract `links` and `emails`.
- Persistence: store `job_posts` with timestamp, sender, message, links, emails.
- Enrichment: fetch linked page text and compute relevance score to profile context.
- User profile management: upsert a single `user_profile` from environment variables; stores profile context and resume bytes for attachment.
- Email actions:
  - Tailored email generation via Groq (OpenAI-compatible) using `GROQ_API_KEY` and `GROQ_MODEL`.
  - SMTP send with optional resume attachment pulled from the DB.
- Form filler (experimental): basic Google Form auto-fill for simple field maps.

## Troubleshooting

- Resume not attached:
  - Ensure `USER_RESUME_PATH` is an absolute path and the file exists.
  - Run `alembic upgrade head` so `user_profile` has `resume_*` columns.
  - After changing `USER_RESUME_PATH`, rerun the pipeline to refresh the stored resume.
- LLM not generating emails:
  - Verify `GROQ_API_KEY` is set; optionally set `GROQ_BASE_URL` and `GROQ_MODEL`.
  - Confirm `openai` package is installed (`pip install -r requirements.txt`).
- DB column errors:
  - Run `alembic upgrade head` to apply migrations.



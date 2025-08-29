import io, json, os
from pypdf import PdfReader
from openai import OpenAI
from firecrawl import Firecrawl
from src.db.session import get_db
from src.models.models import UserProfile

client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))

fc = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

def read_resume(resume_bytes):
    reader = PdfReader(io.BytesIO(resume_bytes))
    return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])

def scrape_url(url):
    try:
        return fc.scrape_url(url).get("text", "")
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def build_summary_prompt(sources):
    src_text = "\n\n".join([f"[{label}] {text}" for label, text in sources])
    return f"""
You are an expert career profiler. Create a structured professional summary.

Requirements:
- A short professional bio (2 sentences).
- 3–6 bullet points highlighting strongest skills, experiences, achievements.
- Avoid filler, focus on evidence from sources.

Sources:
{src_text}

Return strictly in JSON with keys: bio, bullets[]
"""

def enrich_profile(user: UserProfile, db):
    sources = []

    if user.resume_bytes:
        resume_text = read_resume(user.resume_bytes)[:8000]
        sources.append(("Resume", resume_text))

    for link in [user.github, user.linkedin, user.twitter]:
        if link:
            sources.append((link, scrape_url(link)))

    if user.past_work_links:
        for url in json.loads(user.past_work_links):
            sources.append((url, scrape_url(url)[:5000]))

    summary_prompt = build_summary_prompt(sources)
    resp = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an expert job profile analyzer."},
            {"role": "user", "content": summary_prompt},
        ],
        temperature=0.5,
        max_tokens=800,
    )

    profile_context = json.loads(resp.choices[0].message.content)
    user.profile_context = profile_context
    db.commit()
    return user

import os
from typing import Tuple
from openai import OpenAI


from src.utils.llm_client import get_llm_client, get_default_model


def generate_email_subject_body(*, profile_name: str, profile_email: str, profile_context: str | None, job_summary: str, job_link: str | None = None) -> Tuple[str, str]:
    """Use Groq (OpenAI-compatible) to write a tailored email subject and body.

    Returns (subject, body).
    """
    model = get_default_model()
    client = get_llm_client()

    instructions = (
        "You are an expert job application assistant. Write a concise, compelling email that is personalized to the role. "
        "Avoid generic filler. Use a professional tone. 120-220 words."
    )

    context_lines = [
        f"Candidate: {profile_name} <{profile_email}>",
    ]
    if profile_context:
        context_lines.append(f"Profile Context: {profile_context}")
    if job_link:
        context_lines.append(f"Job Link: {job_link}")
    context_lines.append(f"Job Summary: {job_summary[:2000]}")

    system_msg = instructions
    user_msg = "\n".join(context_lines) + (
        "\n\nReturn your result strictly in this format:" \
        "\n<subject>Subject line here</subject>" \
        "\n<body>Body text here</body>"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.6,
        max_tokens=600,
    )
    text = resp.choices[0].message.content or ""

    # Parse simple tags
    def _extract(tag: str) -> str:
        start = text.find(f"<{tag}>")
        end = text.find(f"</{tag}>")
        if start != -1 and end != -1 and end > start:
            return text[start + len(tag) + 2:end].strip()
        return ""

    subject = _extract("subject") or f"Application – {profile_name}"
    body = _extract("body") or text.strip()
    return subject, body



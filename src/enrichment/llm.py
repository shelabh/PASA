# src/enrichment/llm.py
import os
import json
from openai import OpenAI

from src.utils.llm_client import get_llm_client, get_default_model


def analyze_content(text: str, context_type: str = "user", model: str | None = None) -> str:
    """
    Analyze raw scraped text and return a JSON string.
    context_type = "user" or "company"
    - For 'user': returns {"bio": "...", "bullets": ["..", ".."]}
    - For 'company': returns {"summary": "...", "culture": "...", "products": ["..."], "highlights": ["..."]}
    If model output cannot be parsed as JSON, returns a JSON string with raw field.
    """
    if not text or not text.strip():
        return json.dumps({})

    client = get_llm_client()
    model = model or get_default_model()

    if context_type == "user":
        system = "You are an expert career profiler. Extract the most relevant professional info from the text."
        user_instructions = (
            "Produce a JSON object with keys:\n"
            '- "bio": 1-2 sentence professional bio.\n'
            '- "bullets": list of 3-6 concise achievement/skill bullets (evidence based).\n'
            "Avoid filler. Use concrete evidence. Return STRICT JSON only."
        )
    else:
        system = "You are an expert company analyst. Extract the company's key info from the text."
        user_instructions = (
            "Produce a JSON object with keys:\n"
            '- "summary": 1-2 sentence overview of what the company does.\n'
            '- "culture": 1 sentence on company culture or values (if detectable).\n'
            '- "products": list of 1-5 product/service names or descriptions.\n'
            '- "highlights": list of 1-5 short notable facts about the company.\n'
            "Return STRICT JSON only."
        )

    prompt = f"{user_instructions}\n\nSource text:\n{(text[:20000])}"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )

    raw = (resp.choices[0].message.content or "").strip()

    # Try to parse JSON; if fails, wrap raw output
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        # Try to extract JSON substring
        import re
        m = re.search(r"(\{(?:.|\s)*\})", raw)
        if m:
            try:
                parsed = json.loads(m.group(1))
                return json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass
    # fallback: return raw inside a field
    return json.dumps({"raw": raw})

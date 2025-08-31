# src/nlp/job_fit.py
import os
import json
import re
import logging
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


from src.utils.llm_client import get_llm_client, get_default_model


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Try several strategies to extract/parse JSON from model output.
    Returns dict on success, otherwise None.
    """
    if not text:
        return None

    text = text.strip()

    # 1) Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) Find first {...} JSON substring (lazy but often works)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            # fallthrough to regex
            pass

    # 3) regex search for the first JSON object-looking substring (handles backticks/markdown)
    m = re.search(r"(\{(?:.|\s)*\})", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    return None


def _normalize_score(raw: Any) -> int:
    """
    Normalize score into integer 0-100. Accepts int, float, or string like '85', '85%', '0.85'.
    On failure, returns 0.
    """
    if raw is None:
        return 0
    if isinstance(raw, int):
        return max(0, min(100, raw))
    if isinstance(raw, float):
        # interpret float as either 0..1 or 0..100
        if 0 <= raw <= 1:
            return int(raw * 100)
        return int(max(0, min(100, raw)))
    if isinstance(raw, str):
        s = raw.strip()
        # remove percent sign and spaces
        s = s.replace("%", "")
        # keep digits and dot
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        if match:
            try:
                val = float(match.group(0))
                if 0 <= val <= 1:
                    return int(val * 100)
                return int(max(0, min(100, val)))
            except Exception:
                pass
    return 0


def evaluate_job_fit(
    profile_context: Union[Dict[str, Any], str],
    job_description: str,
    model: Optional[str] = None,
    max_tokens: int = 400,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Evaluate candidate fit for a job posting using LLM.
    - profile_context: either dict with keys "bio", "bullets" or a JSON string; falls back to using string as bio.
    - job_description: raw text of the job posting / company context.

    Returns a dict with at least:
    {
      "score": int(0-100),
      "chance": "low"|"medium"|"high",
      "reason": "short justification",
      "match_highlights": ["..."],
      "recommended_email_style": "brief"|"detailed"|"bulleted",
      "raw": "<raw model text>"
    }
    """
    client = get_llm_client()
    model = model or get_default_model()

    # Normalize profile_context
    if isinstance(profile_context, str):
        try:
            profile_context = json.loads(profile_context)
        except Exception:
            profile_context = {"bio": profile_context, "bullets": []}
    bio = profile_context.get("bio", "") if isinstance(profile_context, dict) else ""
    bullets = profile_context.get("bullets", []) if isinstance(profile_context, dict) else []

    bullets_text = "\n".join(f"- {b}" for b in bullets) if bullets else ""

    system_msg = (
        "You are an objective and concise hiring analyst. Produce a compact JSON evaluation of "
        "how well this candidate fits the provided job description. Be evidence-based and reference "
        "items from the candidate profile where relevant."
    )

    user_prompt = f"""Candidate profile:
Bio: {bio}
Bullets:
{bullets_text}

Job description:
{job_description}

Task:
Return ONLY a JSON object (no explanation) with keys:
- score: integer 0-100 (relevance)
- chance: one of "low", "medium", or "high" (likelihood of shortlisting)
- reason: 1-2 sentence justification using evidence from profile/job
- match_highlights: array of 1-5 short strings pointing to profile lines or JD phrases that explain fit
- recommended_email_style: one of "brief", "detailed", "bulleted"
Example:
{{"score": 82, "chance": "high", "reason": "...", "match_highlights": ["..."], "recommended_email_style": "detailed"}}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw_text = (resp.choices[0].message.content or "").strip()
    parsed = _extract_json_from_text(raw_text)

    if parsed is None:
        logger.warning("Could not parse JSON from model. Returning fallback with raw text.")
        return {
            "score": 0,
            "chance": "low",
            "reason": "Could not parse model output.",
            "match_highlights": [],
            "recommended_email_style": "brief",
            "raw": raw_text,
        }

    # Normalize and validate fields
    score = _normalize_score(parsed.get("score"))
    chance = parsed.get("chance", "low")
    if isinstance(chance, str):
        chance = chance.lower()
        if chance not in ("low", "medium", "high"):
            # try mapping
            if score >= 75:
                chance = "high"
            elif score >= 40:
                chance = "medium"
            else:
                chance = "low"
    reason = parsed.get("reason", "").strip()
    match_highlights = parsed.get("match_highlights", [])
    if not isinstance(match_highlights, list):
        match_highlights = [str(match_highlights)]

    recommended_email_style = parsed.get("recommended_email_style", "brief")
    if recommended_email_style not in ("brief", "detailed", "bulleted"):
        # try to coerce common words
        style = str(recommended_email_style).lower()
        if "bullet" in style:
            recommended_email_style = "bulleted"
        elif "brief" in style or "short" in style:
            recommended_email_style = "brief"
        else:
            recommended_email_style = "detailed"

    out = {
        "score": int(score),
        "chance": chance,
        "reason": reason,
        "match_highlights": match_highlights,
        "recommended_email_style": recommended_email_style,
        "raw": raw_text,
    }
    return out


if __name__ == "__main__":
    # quick local test example
    sample_profile = {
        "bio": "Software engineer with 5 years building data pipelines and integrating LLMs in production.",
        "bullets": [
            "5 years Python",
            "Built scalable ETL pipelines",
            "Experience deploying LLMs to production",
        ],
    }
    sample_job = "Looking for a backend engineer with Python, ETL experience, and familiarity with ML/LLMs."
    result = evaluate_job_fit(sample_profile, sample_job)
    print(json.dumps(result, indent=2))

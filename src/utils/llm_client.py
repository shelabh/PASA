# src/utils/llm_client.py
import os
from openai import OpenAI


def get_llm_client() -> OpenAI:
    """
    Returns an OpenAI-compatible client (Groq / OpenAI wrapper).
    Expects GROQ_API_KEY and optional GROQ_BASE_URL in env.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def get_default_model() -> str:
    """Get the default LLM model from environment variables."""
    return os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

# src/enrichment/page_fetcher.py
import requests
from bs4 import BeautifulSoup


def fetch_text(url: str) -> str:
    """
    Fetch and extract visible text from a webpage.
    Falls back gracefully if the page can't be fetched.
    """
    if not url or not url.startswith(("http://", "https://")):
        return ""

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[page_fetcher] Error fetching {url}: {e}")
        return ""

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        return text[:5000]  # avoid overly long content
    except Exception as e:
        print(f"[page_fetcher] Error parsing {url}: {e}")
        return ""

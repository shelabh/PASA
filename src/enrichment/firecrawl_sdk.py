# src/enrichment/firecrawl_sdk.py
"""
Alternative Firecrawl implementation using the official Python SDK.
This follows the exact pattern shown in the Firecrawl documentation.
"""

import os
from typing import Optional

try:
    from firecrawl import Firecrawl
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("⚠️ Firecrawl SDK not installed. Run: pip install firecrawl-py")

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")


def scrape_with_sdk(url: str, max_chars: int = 5000) -> Optional[str]:
    """
    Scrape a URL using the official Firecrawl Python SDK.
    This follows the exact pattern from the documentation.
    """
    if not FIRECRAWL_AVAILABLE:
        print("[firecrawl-sdk] SDK not available")
        return None
        
    if not FIRECRAWL_API_KEY:
        print("[firecrawl-sdk] No API key provided")
        return None
    
    try:
        print(f"[firecrawl-sdk] Initializing Firecrawl client...")
        firecrawl = Firecrawl(api_key=FIRECRAWL_API_KEY)
        
        print(f"[firecrawl-sdk] Scraping {url}...")
        doc = firecrawl.scrape(url, formats=["markdown", "html"])
        
        if doc and hasattr(doc, 'markdown') and doc.markdown:
            content = doc.markdown[:max_chars]
            print(f"[firecrawl-sdk] Successfully scraped {len(content)} characters from {url}")
            return content
        else:
            print(f"[firecrawl-sdk] No markdown content returned for {url}")
            return None
            
    except Exception as e:
        print(f"[firecrawl-sdk] Error scraping {url}: {e}")
        return None


def test_sdk_connectivity():
    """Test function using the official SDK."""
    print("=== Firecrawl SDK Connectivity Test ===")
    print(f"SDK available: {'Yes' if FIRECRAWL_AVAILABLE else 'No'}")
    print(f"API Key available: {'Yes' if FIRECRAWL_API_KEY else 'No'}")
    
    if FIRECRAWL_AVAILABLE and FIRECRAWL_API_KEY:
        test_url = "https://example.com"
        print(f"Testing with: {test_url}")
        result = scrape_with_sdk(test_url)
        if result:
            print("✅ Firecrawl SDK test: SUCCESS")
            print(f"   Content preview: {result[:100]}...")
        else:
            print("❌ Firecrawl SDK test: FAILED")
    else:
        if not FIRECRAWL_AVAILABLE:
            print("💡 Install SDK: pip install firecrawl-py")
        if not FIRECRAWL_API_KEY:
            print("💡 Set FIRECRAWL_API_KEY environment variable")


if __name__ == "__main__":
    test_sdk_connectivity()

# src/enrichment/scraper.py
import os
import json
import requests
import socket
from typing import Optional

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
# Updated to the correct Firecrawl API endpoint (v2)
FIRECRAWL_BASE = os.getenv("FIRECRAWL_BASE", "https://api.firecrawl.dev/v2")


def _check_network_connectivity(host: str, port: int = 443) -> bool:
    """Check if we can connect to a host."""
    try:
        socket.create_connection((host, port), timeout=5)
        return True
    except (socket.timeout, socket.error):
        return False

def _firecrawl_scrape(url: str) -> Optional[str]:
    if not FIRECRAWL_API_KEY:
        print("[firecrawl] No API key provided, skipping Firecrawl")
        return None
    
    # Extract hostname from FIRECRAWL_BASE
    from urllib.parse import urlparse
    parsed_url = urlparse(FIRECRAWL_BASE)
    hostname = parsed_url.hostname
    
    # Check network connectivity first
    if not _check_network_connectivity(hostname):
        print(f"[firecrawl] Cannot connect to {hostname}, skipping Firecrawl")
        return None
    
    # Check if URL is likely to be blocked by Firecrawl
    blocked_domains = ['linkedin.com', 'x.com', 'twitter.com', 'facebook.com', 'instagram.com']
    url_domain = urlparse(url).netloc.lower()
    if any(domain in url_domain for domain in blocked_domains):
        print(f"[firecrawl] Skipping {url} - likely blocked by Firecrawl")
        return None
    
    try:
        print(f"[firecrawl] Attempting to scrape {url} via {FIRECRAWL_BASE}")
        resp = requests.post(
            f"{FIRECRAWL_BASE}/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"},
            json={
                "url": url,
                "formats": ["markdown", "html"],
                "timeout": 30000
            },
            timeout=30,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            # Check if the response has the expected structure
            if data.get("success") and data.get("data"):
                # Extract markdown content as per Firecrawl v2 API
                markdown_content = data["data"].get("markdown", "")
                if markdown_content:
                    print(f"[firecrawl] Successfully scraped {len(markdown_content)} characters from {url}")
                    return markdown_content
                else:
                    print(f"[firecrawl] No markdown content found in response for {url}")
            else:
                print(f"[firecrawl] Unexpected response structure: {data}")
        elif resp.status_code == 403:
            print(f"[firecrawl] Website blocked by Firecrawl: {url}")
            return None
        else:
            print(f"[firecrawl] HTTP {resp.status_code} error: {resp.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"[firecrawl] Connection error scraping {url}: {e}")
    except requests.exceptions.Timeout as e:
        print(f"[firecrawl] Timeout error scraping {url}: {e}")
    except Exception as e:
        print(f"[firecrawl] Unexpected error scraping {url}: {e}")
    
    return None


def _requests_scrape(url: str) -> Optional[str]:
    try:
        print(f"[requests] Attempting to scrape {url} via direct requests")
        
        # Enhanced headers to avoid bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        r = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        
        if r.status_code == 200:
            print(f"[requests] Successfully scraped {len(r.text)} characters from {url}")
            return r.text
        elif r.status_code == 999:
            print(f"[requests] LinkedIn anti-bot protection (HTTP 999) for {url}")
            return None
        elif r.status_code == 403:
            print(f"[requests] Access forbidden (HTTP 403) for {url}")
            return None
        elif r.status_code == 404:
            print(f"[requests] Page not found (HTTP 404) for {url}")
            return None
        else:
            print(f"[requests] HTTP {r.status_code} error for {url}")
    except requests.exceptions.ConnectionError as e:
        print(f"[requests] Connection error scraping {url}: {e}")
    except requests.exceptions.Timeout as e:
        print(f"[requests] Timeout error scraping {url}: {e}")
    except Exception as e:
        print(f"[requests] Unexpected error scraping {url}: {e}")
    return None


def _is_valid_url(url: str) -> bool:
    """Check if URL is valid and likely to be accessible."""
    if not url or not url.strip():
        return False
    
    # Check if it's a valid URL format
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check for common invalid patterns
        invalid_patterns = ['example.com', 'forms.gle/example', 'company.com/apply']
        if any(pattern in url.lower() for pattern in invalid_patterns):
            return False
            
        return True
    except Exception:
        return False

def scrape_url(url: str, max_chars: int = 5000, use_sdk: bool = False) -> str:
    """
    Scrape a URL and return plain text (first max_chars chars). Uses Firecrawl if available.
    
    Args:
        url: URL to scrape
        max_chars: Maximum characters to return
        use_sdk: If True, try to use the official Firecrawl SDK first
    """
    if not url:
        return ""
    
    url = url.strip()
    
    # Validate URL before attempting to scrape
    if not _is_valid_url(url):
        print(f"[scraper] Invalid or test URL detected: {url}")
        return ""
    
    print(f"[scraper] Starting to scrape: {url}")
    
    result = None
    
    # Try Firecrawl SDK first if requested and available
    if use_sdk and FIRECRAWL_API_KEY:
        try:
            from .firecrawl_sdk import scrape_with_sdk
            print(f"[scraper] Attempting Firecrawl SDK scraping...")
            result = scrape_with_sdk(url, max_chars)
        except ImportError:
            print(f"[scraper] Firecrawl SDK not available, falling back to REST API")
    
    # Try Firecrawl REST API if SDK failed or not requested
    if not result and FIRECRAWL_API_KEY:
        print(f"[scraper] Attempting Firecrawl REST API scraping...")
        result = _firecrawl_scrape(url)
    
    # Fallback to direct requests if Firecrawl fails or is not available
    if not result:
        print(f"[scraper] Firecrawl failed or unavailable, trying direct requests...")
        result = _requests_scrape(url) or ""
    
    # Trim to max_chars to reduce LLM token usage
    final_result = result[:max_chars]
    print(f"[scraper] Final result: {len(final_result)} characters")
    
    return final_result


def test_firecrawl_connectivity():
    """Test function to check Firecrawl connectivity and configuration."""
    print("=== Firecrawl Connectivity Test ===")
    print(f"API Key available: {'Yes' if FIRECRAWL_API_KEY else 'No'}")
    print(f"Base URL: {FIRECRAWL_BASE}")
    
    if FIRECRAWL_API_KEY:
        from urllib.parse import urlparse
        parsed_url = urlparse(FIRECRAWL_BASE)
        hostname = parsed_url.hostname
        print(f"Hostname: {hostname}")
        
        if _check_network_connectivity(hostname):
            print("✅ Network connectivity: OK")
        else:
            print("❌ Network connectivity: FAILED")
            
        # Test with a simple URL
        test_url = "https://example.com"
        print(f"Testing with: {test_url}")
        result = _firecrawl_scrape(test_url)
        if result:
            print("✅ Firecrawl test: SUCCESS")
            print(f"   Content preview: {result[:100]}...")
        else:
            print("❌ Firecrawl test: FAILED")
            
        # Test with a more complex URL
        test_url2 = "https://firecrawl.dev"
        print(f"Testing with: {test_url2}")
        result2 = _firecrawl_scrape(test_url2)
        if result2:
            print("✅ Firecrawl test 2: SUCCESS")
            print(f"   Content preview: {result2[:100]}...")
        else:
            print("❌ Firecrawl test 2: FAILED")
    else:
        print("⚠️ No API key provided")
        print("💡 Set FIRECRAWL_API_KEY environment variable to test")


if __name__ == "__main__":
    test_firecrawl_connectivity()

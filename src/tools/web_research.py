"""Web research tools for competitor analysis and market research."""

import json
import re
from typing import Optional
from urllib.parse import urlparse, quote_plus

from langchain_core.tools import tool

# Try to import httpx for web requests, fall back gracefully
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


def _extract_text_from_html(html: str, max_length: int = 5000) -> str:
    """Extract readable text from HTML content."""
    if BS4_AVAILABLE:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
    else:
        # Basic fallback: remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "...[truncated]"

    return text


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for competitor and market research.

    Uses DuckDuckGo's HTML interface for search results.
    Useful for competitor analysis, feature research, and market trends.

    Args:
        query: The search query string
        num_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    if not HTTPX_AVAILABLE:
        return "Error: httpx library not installed. Install with: pip install httpx"

    try:
        # Use DuckDuckGo HTML endpoint (no API key required)
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(search_url, headers=headers, follow_redirects=True)
            response.raise_for_status()

        if not BS4_AVAILABLE:
            return "Error: beautifulsoup4 not installed. Install with: pip install beautifulsoup4"

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Parse DuckDuckGo results
        for i, result in enumerate(soup.select(".result")):
            if i >= num_results:
                break

            title_elem = result.select_one(".result__title a")
            snippet_elem = result.select_one(".result__snippet")

            if title_elem:
                title = title_elem.get_text(strip=True)
                # DuckDuckGo wraps URLs, try to extract actual URL
                href = title_elem.get("href", "")
                if "uddg=" in href:
                    # Extract actual URL from redirect
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    url = parsed.get("uddg", [href])[0]
                else:
                    url = href

                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(f"**{title}**\nURL: {url}\n{snippet}\n")

        if not results:
            return f"No results found for: {query}"

        return f"## Search Results for: {query}\n\n" + "\n---\n".join(results)

    except httpx.TimeoutException:
        return "Error: Search request timed out"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error performing web search: {str(e)}"


@tool
def web_fetch(url: str, extract_text: bool = True) -> str:
    """Fetch and extract content from a URL.

    Retrieves the content of a web page and optionally extracts readable text.
    Useful for analyzing competitor documentation, feature pages, etc.

    Args:
        url: The URL to fetch
        extract_text: Whether to extract text from HTML (default: True)

    Returns:
        Page content as text or HTML
    """
    if not HTTPX_AVAILABLE:
        return "Error: httpx library not installed. Install with: pip install httpx"

    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
        elif parsed.scheme not in ["http", "https"]:
            return f"Error: Invalid URL scheme. Use http or https."
    except Exception:
        return f"Error: Invalid URL format: {url}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        # Handle JSON responses
        if "application/json" in content_type:
            try:
                data = response.json()
                return f"## JSON Content from {url}\n\n```json\n{json.dumps(data, indent=2)[:5000]}\n```"
            except json.JSONDecodeError:
                return response.text[:5000]

        # Handle HTML responses
        if extract_text and "text/html" in content_type:
            text = _extract_text_from_html(response.text)
            return f"## Content from {url}\n\n{text}"

        # Return raw text for other content types
        return f"## Content from {url}\n\n{response.text[:5000]}"

    except httpx.TimeoutException:
        return f"Error: Request to {url} timed out"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} from {url}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


@tool
def analyze_competitors(product_type: str, num_competitors: int = 3) -> str:
    """Search for and analyze competitors for a given product type.

    Performs a web search to find competitors and provides a summary.
    Useful for the competitor research section of PRDs.

    Args:
        product_type: Type of product to research (e.g., "task management app")
        num_competitors: Number of competitors to find (default: 3)

    Returns:
        Formatted competitor analysis
    """
    # Search for competitors
    search_query = f"best {product_type} alternatives comparison"
    search_results = web_search.invoke({"query": search_query, "num_results": num_competitors * 2})

    return f"""## Competitor Analysis: {product_type}

### Search Results
{search_results}

### Analysis Notes
To complete the competitor analysis:
1. Review the search results above
2. Identify the main competitors mentioned
3. Note their key features and differentiators
4. Identify gaps our product could fill

*Note: For detailed competitor features, use web_fetch to visit specific competitor pages.*
"""

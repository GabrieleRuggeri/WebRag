from typing import List, Optional
import logging
import time
import re
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup, Comment
from urllib.parse import unquote

"""
Simple, well-documented WebRetriever class that:
- searches the web for top result links (uses DuckDuckGo HTML)
- fetches and extracts visible text from a web page

Dependencies:
- requests
- beautifulsoup4
"""



logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WebRetriever:
    """
    WebRetriever provides two simple behaviors:

    - search(query: str, num_result: int) -> List[str]
      Performs a web search (DuckDuckGo HTML) and returns a list of top result URLs.

    - parse(path: str) -> str
      Fetches a web page and returns its visible text content.
    """

    DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/"

    def __init__(self, timeout: float = 10.0, max_retries: int = 3, backoff_factor: float = 0.3):
        """
        timeout: seconds for HTTP requests
        max_retries: number of retries for transient failures
        backoff_factor: sleep factor between retries
        """
        self.timeout = float(timeout)
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"])
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Basic header to reduce blocking
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WebRetriever/1.0; +https://example.local/)"
        })

    def _clean_link(self, link: str) -> Optional[str]:
        """
        Normalize and validate a link. Returns None for obviously invalid links.
        """
        if not link:
            return None
        link = link.strip()
        # ignore javascript/mailto/tel etc.
        if link.startswith(("javascript:", "mailto:", "tel:")):
            return None
        # ensure it has a scheme
        parsed = urlparse(link)
        if not parsed.scheme:
            # assume http if scheme missing
            link = "http://" + link
            parsed = urlparse(link)
        if not parsed.netloc:
            return None
        return link

    def search(self, query: str, num_result: int = 10) -> List[str]:
        """
        Search the web for `query` and return up to `num_result` result URLs.

        Implementation notes:
        - Uses DuckDuckGo's lightweight HTML interface for scraping stability.
        - Filters and deduplicates URLs, preserves order.
        - Returns an empty list on errors.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(num_result, int) or num_result <= 0:
            raise ValueError("num_result must be a positive integer")

        params = {"q": query}
        try:
            resp = self.session.get(self.DUCKDUCKGO_HTML, params=params, timeout=self.timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            links = []
            seen = set()

            # DuckDuckGo's HTML result anchors often appear as <a class="result__a" href="...">
            # Fallback: collect all <a href> that look like external links.
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # DuckDuckGo sometimes uses '/l/?kh=-1&uddg=<encoded-url>' for redirect links.
                # Try to extract real URL if present (uddg param) otherwise take href directly.
                # A simple approach: prefer hrefs that are full URLs.
                if "uddg=" in href:
                    # attempt to extract after uddg=
                    m = re.search(r"uddg=([^&]+)", href)
                    if m:
                        try:
                            href = unquote(m.group(1))
                        except Exception:
                            pass

                clean = self._clean_link(href)
                if not clean:
                    continue
                if clean in seen:
                    continue
                seen.add(clean)
                links.append(clean)
                if len(links) >= num_result:
                    break

            return links[:num_result]
        except Exception as e:
            logger.debug("search failed for query=%r: %s", query, e)
            return []

    def parse(self, path: str) -> str:
        """
        Fetch the page at `path` and extract visible text content.

        Returns a single string of text (whitespace normalized). On error returns an empty string.
        """
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")

        url = path.strip()
        if not urlparse(url).scheme:
            url = "http://" + url  # assume http if missing

        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            # Respect content-type: only parse HTML-ish pages
            content_type = resp.headers.get("Content-Type", "").lower()
            if "html" not in content_type and "text" not in content_type:
                logger.debug("parse: content-type not HTML/text: %s", content_type)
                return ""

            soup = BeautifulSoup(resp.content, "html.parser")

            # Remove scripts, styles, and comments
            for element in soup(["script", "style", "noscript", "header", "footer", "nav", "meta", "svg", "iframe"]):
                element.decompose()
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Extract visible text and normalize whitespace
            text = soup.get_text(separator=" ", strip=True)
            # collapse multiple whitespace
            text = re.sub(r"\s+", " ", text).strip()

            return text
        except Exception as e:
            logger.debug("parse failed for url=%r: %s", url, e)
            return ""
        
if __name__ == "__main__":
    retriever = WebRetriever()

    # Example search
    query = "OpenAI GPT-4"
    print(f"Searching for: {query}")
    results = retriever.search(query, num_result=5)
    for i, link in enumerate(results, 1):
        print(f"{i}. {link}")

    # Example parse
    if results:
        url_to_parse = results[0]
        print(f"\nParsing URL: {url_to_parse}")
        content = retriever.parse(url_to_parse)
        print(f"Extracted content (first 500 chars):\n{content[:500]}")
import os
from tavily import TavilyClient
from utils.logging_config import configure_logging_from_env, get_logger

# Ensure logging is configured according to environment (DEBUG env var)
configure_logging_from_env()
logger = get_logger(__name__)


class WebSearch:
    """Wrapper around the TavilyClient to perform web searches.

    Notes:
    - Reads TAVILY_API_KEY from the environment (or accepts an explicit api_key).
    - Accepts an optional `client` for dependency injection (useful for tests).
    """

    def __init__(self, api_key: str | None = None, client: object | None = None):
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.error("TAVILY_API_KEY is not set in environment")
            raise ValueError("TAVILY_API_KEY is not set")

        # Allow injecting a client (for tests) otherwise create a real TavilyClient
        self.client = client or TavilyClient(api_key=api_key)
        self.logger = logger

    def search(self, query: str, num_results: int = 5) -> list:
        """Perform a web search using the Tavily API.

        Args:
            query (str): The search query.
            num_results (int): Number of search results to return.

        Returns:
            list: A list of search results.
        """
        self.logger.debug("Performing web search: query=%s num_results=%d", query, num_results)
        try:
            results = self.client.search(
                    query=query, 
                    num_results=num_results, 
                    include_images=False, 
                    search_depth="advanced"
                )
            hits = results.get("results", []) if isinstance(results, dict) else results
            self.logger.info("Web search completed: returned %d hits", len(hits))
            return hits
        except Exception as e:
            self.logger.error("Web search failed: %s", str(e))
            raise


if __name__ == "__main__":
    # Example usage
    web_search = WebSearch()
    query = "Latest advancements in AI"
    results = web_search.search(query, num_results=3)
    for i, result in enumerate(results, 1):
        print(f"Result {i}: {result}")


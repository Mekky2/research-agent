from langchain_core.tools import tool
import httpx
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

@tool
def scrape_and_extract(url: str) -> str:
    """Scrapes the text content from a provided URL."""
    print(f"[Tool: Scraper] Scraping URL: {url}")

    # Bare tokens like "ResearchAgentBot/1.0" with no contact info get 403'd
    # by sites that enforce a User-Agent policy (Wikimedia included) -- and
    # the auto-chain in researcher.py scrapes the Wikipedia URL that
    # search.py just found, so this needs to be a compliant identity too.
    # Set USER_AGENT in .env (already done in this project's .env) to
    # override with your own contact info.
    headers = {"User-Agent": os.getenv(
        "USER_AGENT",
        "ResearchAgentBot/1.0 (set USER_AGENT in your .env)"
    )}
    char_limit = int(os.getenv("SCRAPE_CHAR_LIMIT", 10000)) # Limit the number of characters to scrape

    try:
        response = httpx.get(url, headers = headers, timeout = 30.0)
        response.raise_for_status() # Raise an error for response codes 4xx or 5xx

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text from all paragraph tags
        paragraphs = soup.find_all("p")
        text = "\n".join([p.get_text() for p in paragraphs if p.get_text().strip()])

        # Truncate to prevent context window overflow
        if len(text) > char_limit:
            return text[:char_limit] + "\n\n...[Content Truncated]"
        return text
    except Exception as e:
        return f"Scraping failed: {str(e)}"
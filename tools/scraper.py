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

    headers = {"User-Agent": os.getenv("USER_AGENT", "ResearchAgentBot/1.0")}
    char_limit = int(os.getenv("SCRAPER_CHAR_LIMIT", 10000)) # Limit the number of characters to scrape

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
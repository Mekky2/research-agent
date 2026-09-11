import httpx
from bs4 import BeautifulSoup

def scrape_and_extract(url: str) -> str:
    """Fetches a webpage and returns clean text without HTML bloat."""
    try:
        # Use a transparent bot User-Agent to comply with Wikipedia's API policy
        headers = {"User-Agent": "ResearchAgentBot/1.0 (test@example.com)"}
        
        response = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Rip out the garbage that confuses LLMs
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.extract()
            
        text = soup.get_text(separator="\n", strip=True)
        
        # Hard limit the text length to protect the 4096 context window
        return text[:8000] 
        
    except Exception as e:
        print(f"[Scrape Error] {e}")
        return f"Failed to scrape {url}: {str(e)}"
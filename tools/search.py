import httpx
import urllib.parse
from typing import List, Dict

def clean_query(query: str) -> str:
    # Strip common conversational fluff to help keyword search
    fluff = ["find", "the", "latest", "hardware", "specifications", "for", "and", "summarize", "their", "capabilities"]
    words = [w for w in query.split() if w.lower() not in fluff]
    cleaned = " ".join(words).strip()
    return cleaned if cleaned else query

def execute_web_search(query: str, max_results: int = 3) -> List[Dict]:
    """Search tool querying Wikipedia's API with query cleaning."""
    results = []
    try:
        search_term = clean_query(query)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(search_term)}&utf8=&format=json"
        headers = {"User-Agent": "ResearchAgentBot/1.0 (youssef2016tammam@gmail.com)"}
        
        response = httpx.get(search_url, headers=headers, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        search_hits = data.get("query", {}).get("search", [])
        
        for hit in search_hits[:max_results]:
            title = hit["title"]
            url_title = urllib.parse.quote(title.replace(" ", "_"))
            results.append({
                "title": title,
                "url": f"https://en.wikipedia.org/wiki/{url_title}",
                "snippet": hit.get("snippet", "")
            })
            
        return results
        
    except Exception as e:
        print(f"[Search Error] {e}")
        return [{"error": f"Failed to search: {str(e)}"}]
from langchain_core.tools import tool
import httpx
import urllib.parse

@tool
def execute_web_search(query: str) -> str:
    """Searches Wikipedia's full text for a given query and returns the URL of the top result."""
    print(f"   [Tool: Search] Searching for: {query}")
    
    url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&srsearch={urllib.parse.quote(query)}"
        f"&utf8=&format=json&srlimit=1"
    )
    
    try:
        # WIKIPEDIA FIX: Wikimedia blocks automated requests missing a User-Agent header
        headers = {"User-Agent": "LocalResearchAgent/1.0 (local-dev)"}
        response = httpx.get(url, headers=headers, timeout=10.0)
        
        # This will catch HTTP 403 Forbidden errors if they occur
        response.raise_for_status() 
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        
        if search_results:
            top_title = search_results[0]["title"]
            formatted_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(top_title.replace(' ', '_'))}"
            return formatted_url
            
        return "No results found for that query."
    except Exception as e:
        return f"Search failed: {str(e)}"
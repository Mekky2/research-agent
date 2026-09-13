from langchain_core.tools import tool
import httpx
import urllib.parse

@tool
def execute_web_search(query: str) -> str:
    """Searches Wikipedia's full text for a given query and returns the URL of the top result."""
    print(f"   [Tool: Search] Searching for: {query}")
    
    # Upgraded to full-text search ('query' + 'srsearch') instead of title-only 'opensearch'
    url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&srsearch={urllib.parse.quote(query)}"
        f"&utf8=&format=json&srlimit=1"
    )
    
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()
        
        # Check if the full-text search found any matching pages
        search_results = data.get("query", {}).get("search", [])
        
        if search_results:
            # Extract the title of the top match and format it into a valid Wikipedia URL
            top_title = search_results[0]["title"]
            formatted_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(top_title.replace(' ', '_'))}"
            return formatted_url
            
        return "No results found for that query."
    except Exception as e:
        return f"Search failed: {str(e)}"
from langchain_core.tools import tool
import httpx
import urllib.parse

@tool
def execute_web_search(query: str) -> str:
    """Searches Wikipedia for a given query and returns the URL of the top result."""
    print(f"[Tool: Search] Searching for: {query}")

    url = f"https://en.wikipedia.org/w/api.php?action=opensearch@search={urllib.parse.quote(query)}&limit=1&namespace=0&format=json"
    try:
        response = httpx.get(url, timeout=10.0)
        data = response.json()

        # The Wikipedia API returns URLs in the 4th array element
        if len(data) > 3 and data[3]:
            return data[3][0]  # Return the first URL
        return "No results found for that query."
    except Exception as e:
        return f"Search failed: {str(e)}"
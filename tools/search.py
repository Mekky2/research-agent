from langchain_core.tools import tool
import httpx
import time
import urllib.parse

import os
from dotenv import load_dotenv

load_dotenv()  # explicit, not relying on some other module importing first

WIKI_API = "https://en.wikipedia.org/w/api.php"

# Wikimedia's User-Agent policy: a missing, empty, or generic User-Agent gets
# a hard 403 from their servers, regardless of the request being otherwise
# valid. https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
# The format they ask for is "AppName/Version (contact URL or email)".
# Reads the same USER_AGENT your .env already defines for the scraper --
# one identity for both Wikipedia-facing tools. The fallback below is just a
# safety net if USER_AGENT is ever unset; put your real contact in .env
# rather than editing this file, since it's the one likely to end up in git.
_DEFAULT_UA = "ResearchAgentBot/1.0 (set USER_AGENT in your .env)"
HEADERS = {"User-Agent": os.getenv("USER_AGENT", _DEFAULT_UA)}

# Generic words that help a human phrase a query but hurt it here: they
# rarely appear verbatim on the target article, and stacking them onto an
# entity name (e.g. "AMD Ryzen 7 7700X specs") is a common way to knock a
# real, well-documented topic down to zero search results.
_FILLER_WORDS = {
    "specs", "spec", "specification", "specifications", "details", "detail",
    "info", "information", "review", "reviews", "benchmark", "benchmarks",
    "features", "overview", "guide", "about", "explained",
}


def _clean_query(query: str) -> str:
    tokens = [t for t in query.split() if t.lower() not in _FILLER_WORDS]
    return " ".join(tokens) if tokens else query


def _full_text_search(query: str, client: httpx.Client) -> str | None:
    """Relevance-ranked full text search. Good for topics and phrases."""
    url = (
        f"{WIKI_API}?action=query&list=search&srsearch={urllib.parse.quote(query)}"
        f"&utf8=&format=json&srlimit=1"
    )
    response = client.get(url)
    response.raise_for_status()
    results = response.json().get("query", {}).get("search", [])
    if not results:
        return None
    title = results[0]["title"]
    return f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"


def _opensearch(query: str, client: httpx.Client) -> str | None:
    """Title prefix match. More forgiving for exact product/entity names
    than full text search, since it doesn't depend on every word in the
    query appearing in the article body."""
    url = (
        f"{WIKI_API}?action=opensearch&search={urllib.parse.quote(query)}"
        f"&limit=1&namespace=0&format=json"
    )
    response = client.get(url)
    response.raise_for_status()
    data = response.json()
    if len(data) >= 4 and data[3]:
        return data[3][0]
    return None


@tool
def execute_web_search(query: str) -> str:
    """Searches Wikipedia's full text for a given query and returns the URL of the top result."""
    print(f"   [Tool: Search] Searching for: {query}")

    cleaned = _clean_query(query)
    # Try, in order: the filler-stripped query, the original query as given,
    # then just the first two tokens (usually the core entity/product name).
    # Wikipedia's search is picky about exact wording, so a single failed
    # attempt doesn't mean the topic doesn't exist.
    candidates = list(dict.fromkeys(
        [cleaned, query, " ".join(cleaned.split()[:2])]
    ))
    candidates = [c for c in candidates if c.strip()]

    last_error = None

    with httpx.Client(headers=HEADERS, timeout=15.0) as client:
        for candidate in candidates:
            for attempt in range(2):
                try:
                    result = _full_text_search(candidate, client) or _opensearch(candidate, client)
                    if result:
                        return result
                    break  # this candidate got zero results, try the next one
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    # Likely a transient network hiccup -- retry once before
                    # giving up on this candidate.
                    last_error = e
                    time.sleep(1)
                    continue
                except Exception as e:
                    last_error = e
                    break

    # Report WHAT went wrong, not just THAT something went wrong -- "no
    # results for this exact phrase" and "the HTTP request itself failed"
    # need very different fixes, and hiding the distinction (as the previous
    # version did) makes both look identical from the caller's side.
    if last_error:
        return f"Search failed: {type(last_error).__name__}: {last_error}"
    return "No results found for that query."
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field
from tools.search import execute_web_search
from tools.scraper import scrape_and_extract

# 1. The Pydantic Guardrail
class ResearcherAction(BaseModel):
    action: str = Field(description="The tool to use. 'search' to find a topic, 'scrape' to read a specific URL.")
    argument: str = Field(description="A CONCISE 1-3 WORD KEYWORD for search, or a URL for scrape.")

# 2. Initialize LLM
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
    temperature=0.0 
)

researcher_agent = llm.with_structured_output(ResearcherAction)

def run_researcher(state: dict) -> dict:
    print("\n[Researcher] Searching and extracting data...")
    
    sys_msg = SystemMessage(
        content="You are a data retrieval agent. Your goal is to find facts.\n"
        "Set action to 'search' and provide a CONCISE 1-3 WORD KEYWORD."
    )
    
    messages = [sys_msg] + list(state["messages"])
    
    try:
        decision = researcher_agent.invoke(messages)
    except Exception as e:
        print(f"   -> [Error] Model failed to format output: {e}")
        return {
            "extracted_data": state.get("extracted_data", []) + ["Error: Researcher failed to use tools."],
            "messages": [AIMessage(content="I failed to format my tool call correctly.")]
        }
    
    new_messages = []
    extracted = []
    search_failures = state.get("search_failures", 0)
    
    # 3. Tool Execution Logic
    if decision.action == 'search':
        print(f"   -> [Tool Execution] Triggering 'search' with query: {decision.argument}")
        url = execute_web_search.invoke(decision.argument)
        
        if str(url).startswith("http"):
            # AUTO-CHAIN: Search worked, immediately scrape to save the Supervisor a turn
            print(f"   -> [Auto-Chain] Found URL: {url}. Immediately scraping...")
            scrape_data = scrape_and_extract.invoke(url)
            extracted.append(str(scrape_data))
            new_messages.append(AIMessage(content=f"Searched '{decision.argument}', found {url}, and successfully extracted the text data."))
            print(f"   -> [Tool Output] Scraped {len(str(scrape_data))} characters.")
            search_failures = 0  # reset the streak on a real success
        else:
            # `url` here is actually the tool's error/status string (e.g.
            # "No results found for that query." or "Search failed: ...").
            # Print it directly instead of a generic message, since that's
            # the only way to tell "Wikipedia has nothing" apart from
            # "the request itself failed" (timeout, DNS, HTTP error, etc.).
            search_failures += 1
            print(f"   -> [Warning] Search failed ({search_failures}/3 consecutive): {url}")
            extracted.append(f"CRITICAL ERROR: Search failed for '{decision.argument}': {url}")
            new_messages.append(AIMessage(content=f"The search failed: {url}. Stop the workflow. Route to FINISH immediately."))

    elif decision.action == 'scrape':
        print(f"   -> [Tool Execution] Triggering 'scrape' with URL: {decision.argument}")
        scrape_data = scrape_and_extract.invoke(decision.argument)
        extracted.append(str(scrape_data))
        new_messages.append(AIMessage(content=f"Scraped the URL and got the data."))
        print(f"   -> [Tool Output] Scraped {len(str(scrape_data))} characters.")
        
    return {
        "messages": new_messages,
        "extracted_data": state.get("extracted_data", []) + extracted,
        "search_failures": search_failures
    }
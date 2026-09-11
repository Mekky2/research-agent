import time
from core.state import ResearchState
from core.middleware import LLMMiddleware
from tools.search import execute_web_search
from tools.scraper import scrape_and_extract
import httpx

def run_agent(objective: str):
    state = ResearchState(objective=objective)
    brain = LLMMiddleware()
    
    print(f"Starting Agent Objective: {objective}\n")
    
    duplicate_counter = 0
    max_steps = 10
    step = 0
    
    while state.current_status != "complete" and state.current_status != "error" and step < max_steps:
        step += 1
        print(f"\n--- [Step {step}] Status: {state.current_status} ---")
        
        action = brain.decide_next_action(state)
        
        print(f"Action Chosen: {action.tool_name}")
        print(f"Reasoning: {action.reasoning}")
        
        # 1. Web Search
        if action.tool_name == "execute_web_search":
            state.current_status = "researching"
            
            # SMART EXTRACTOR: Catch LLM hallucinations like {"keywords": "..."}
            args = action.tool_arguments
            if isinstance(args, dict):
                query = args.get("query") or args.get("search_query") or args.get("keywords") or args.get("q")
                if not query and args.values(): 
                    query = list(args.values())[0] # Just grab whatever the first value is
                if isinstance(query, list): 
                    query = " ".join(query) # If it gave a list, join it into a string
            else:
                query = str(args)
                
            if query not in state.search_queries_run:
                print(f"   -> Searching for: {query}")
                results = execute_web_search(query)
                state.search_queries_run.append(query)
                
                found_urls = [r["url"] for r in results if isinstance(r, dict) and "url" in r]
                state.draft_report += f"\n[System]: Search returned URLs: {found_urls}. Next action MUST be 'scrape_and_extract' on one of these URLs."
                duplicate_counter = 0
            else:
                duplicate_counter += 1
                print(f"   -> Blocked duplicate search ({duplicate_counter}/2)")
                state.draft_report += "\n[System Directive]: Duplicate search rejected. Call 'scrape_and_extract' with a discovered URL or call 'evaluate_findings'."

        # 2. Web Scraping
        elif action.tool_name == "scrape_and_extract":
            # SMART EXTRACTOR for URLs
            args = action.tool_arguments
            if isinstance(args, dict):
                url = args.get("url") or args.get("link") or args.get("website")
                if not url and args.values():
                    url = list(args.values())[0]
            else:
                url = str(args)
            
            if url and url not in state.visited_urls:
                print(f"   -> Scraping: {url}")
                content = scrape_and_extract(url)
                state.visited_urls.append(url)
                state.current_status = "synthesizing"
                
                state.draft_report += f"\n[Extracted Data from {url}]:\n{content[:6000]}\n"
                state.draft_report += "\n[System Directive]: Data gathered. Do NOT scrape again. Your next action MUST be 'evaluate_findings' or 'finish' to write the final summary."
                duplicate_counter = 0
            else:
                duplicate_counter += 1
                print(f"   -> Blocked duplicate scrape ({duplicate_counter}/2)")
                state.draft_report += "\n[CRITICAL]: You have already scraped this URL! You cannot scrape it again. Call 'evaluate_findings' or 'finish' NOW."

        # 3. Finish / Evaluate
        elif action.tool_name in ["evaluate_findings", "finish"]:
            print("\nAgent has completed research phase.")
            state.current_status = "complete"
            break
            
        else:
            print(f"Unknown tool requested: {action.tool_name}")
            state.current_status = "error"

        if duplicate_counter >= 2:
            print("\n[Middleware Override]: Loop detected. Forcing agent into synthesis mode.")
            state.current_status = "complete"
            break
            
        time.sleep(1)

    # 4. FINAL SYNTHESIS 
    print("\n================ FINAL SYNTHESIS ================")
    print("Writing final report based on gathered intelligence...\n")
    
    final_prompt = f"""You are an AI research assistant. Based on the following raw data gathered by your automated web scraper, write a clean, detailed summary answering the user's objective.
    
User Objective: {objective}

Raw Agent Data:
{state.draft_report}

Write your final summary now:"""

    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:3b", 
                "prompt": final_prompt,
                "stream": False
            },
            timeout=60.0
        )
        response.raise_for_status() 
        
        data = response.json()
        if "error" in data:
            print(f"Ollama Error: {data['error']}")
        else:
            print(data.get("response", "No response generated."))
            
    except Exception as e:
        print(f"Error generating final report: {e}")

if __name__ == "__main__":
    test_objective = "Search for 'Meteor Lake' and 'Lunar Lake' to find the latest Intel Core Ultra hardware specifications and summarize their dedicated NPU machine learning capabilities."
    run_agent(test_objective)
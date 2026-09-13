import os
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field
from tools.search import execute_web_search
from tools.scraper import scrape_and_extract

class ResearcherAction(BaseModel):
    action: str = Field(description="The tool to use. MUST be either 'search' or 'scrape'.")
    argument: str = Field(description="The input for the tool. For 'search', provide a short keyword query. For 'scrape', provide a URL.")

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
    temperature=0.0 
)

researcher_agent = llm.with_structured_output(ResearcherAction)

def run_researcher(state: dict) -> dict:
    print("\n[Researcher] Searching and extracting data...")
    
    sys_msg = SystemMessage(
        content="You are a data retrieval agent.\n"
        "CRITICAL RULES:\n"
        "1. Look at the Supervisor's instructions. If the Supervisor gives you a URL, you MUST set action to 'scrape' and use that exact URL.\n"
        "2. If there is NO URL in the Supervisor's instructions, set action to 'search' and provide a CONCISE 1-3 WORD KEYWORD (e.g., 'Arrow Lake').\n"
        "Respond ONLY with the required JSON structured data."
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
    tool_result = ""
    
    if decision.action == 'search':
        print(f"   -> [Tool Execution] Triggering 'search' with query: {decision.argument}")
        tool_result = execute_web_search.invoke(decision.argument)
        # CRITICAL FIX: We put the URL in the chat history so the LLM sees it, 
        # but we DO NOT add it to extracted_data
        new_messages.append(AIMessage(content=f"Search Result URL: {tool_result}. Next step: I must scrape this URL."))
        
    elif decision.action == 'scrape':
        print(f"   -> [Tool Execution] Triggering 'scrape' with URL: {decision.argument}")
        tool_result = scrape_and_extract.invoke(decision.argument)
        # CRITICAL FIX: Only actual scraped text triggers the 'has_data' state flag
        extracted.append(str(tool_result))
        new_messages.append(AIMessage(content=f"I scraped the URL and got the data."))
        
    else:
        print(f"   -> [Warning] Invalid action chosen: {decision.action}")
        tool_result = "Failed"
        
    print(f"   -> [Tool Output] Retrieved {len(str(tool_result))} characters.")
    
    return {
        "messages": new_messages,
        "extracted_data": state.get("extracted_data", []) + extracted
    }
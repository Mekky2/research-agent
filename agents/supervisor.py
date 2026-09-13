import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from state import SupervisorDecision

load_dotenv()

# 1. Initialize the local model
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
    temperature=0.0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

# 2. Bind structured output
supervisor_agent = llm.with_structured_output(SupervisorDecision)

# 3. System prompt definition
system_prompt = (
    "You are the Supervisor of an autonomous research team.\n"
    "Your sole job is to manage the workflow and delegate tasks to the following workers:\n\n"
    "1. 'Researcher': Call this agent when you need to search the web or scrape data.\n"
    "2. 'Verifier': Call this agent to evaluate the extracted data against the original objective.\n"
    "3. 'Memory': Call this agent ONLY when data is verified and you need to save the final report to disk.\n"
    "4. 'FINISH': Route here ONLY when the objective is completely satisfied, verified, and saved.\n\n"
    "Analyze the conversation history and decide who acts next. Provide explicit instructions for the selected worker."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="messages"),
    (
        "system",
        "CURRENT WORKFLOW STATE:\n"
        "- Has the Researcher extracted data yet?: {has_data}\n"
        "- What is the Verifier's status?: {verification_status}\n\n"
        "CRITICAL RULES:\n"
        "1. If there is NO 'Search Result URL' in the chat history, instruct the Researcher to SEARCH. NEVER make up, guess, or invent a URL.\n"
        "2. If there IS a 'Search Result URL' in the chat history, instruct the Researcher to SCRAPE and paste that exact URL into your instructions.\n"
        "3. If 'has_data' is YES, route to the Verifier.\n\n"
        "Given the conversation above and the current state, who should act next?\n"
        "Respond ONLY with the Pydantic structured output."
    )
])

# 4. Pipe: dictionary -> prompt -> structured model
supervisor_chain = prompt | supervisor_agent

def run_supervisor(state: dict) -> dict:
    """The LangGraph node function that executes the Supervisor."""
    print("\n[Supervisor] Analyzing state and making routing decision...")

    has_data = "YES" if state.get("extracted_data") else "NO"
    verification_status = state.get("verification_status") or "PENDING"

    decision = supervisor_chain.invoke({
        "messages": state["messages"],
        "has_data": has_data,
        "verification_status": verification_status
    })

    print(f"   -> Routing to: {decision.next_agent}")
    print(f"   -> Instructions: {decision.instructions}")

    return {
        "next_agent": decision.next_agent,
        "messages": [SystemMessage(content=f"Supervisor Instructions: {decision.instructions}")]
    }
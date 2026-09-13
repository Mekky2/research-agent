import os
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from tools.file_ops import save_report

# 1. Initialize the LLM
llm = ChatOllama(
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
    temperature = 0.1
)

# 2. Define the exact role
memory_system_message = (
    "You are the Memory Agent. Your hob is to compile the verfied research into a clean, "
    "well-structured final report and save it to the disk using the save_report tool.\n"
    "Look at the conversation history, extract the factual findings, format them nicely, "
    "and execute the tool to save the file."
)

# 3. Equip the agent with the file operation tool
memory_agent = create_react_agent(
    llm,
    tools = [save_report],
    prompt=memory_system_message
)

def run_memory(state: dict) -> dict:
    """Formats the final data and writes it to the local disk."""
    print("\n [Memory] Compiling and saving the final report...")

    # Run the agent to format the text and call the save tool
    result = memory_agent.invoke({"messages": state["messages"]})

    # Isolate only the new messages generated during this turn to append to state
    new_messages = result["messages"][len(state["messages"]):]

    return {"messages": new_messages}
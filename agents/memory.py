import os
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.file_ops import save_report

# 1. Initialize the LLM
llm = ChatOllama(
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b"),
    temperature = 0.1
)

# 2. Define the exact role
memory_system_message = (
    "You are the Memory Agent. Your job is to compile the verified research into a clean, "
    "well-structured final report and save it to the disk using the save_report tool.\n"
    "Look at the conversation history, extract the factual findings, format them nicely, "
    "and execute the tool to save the file."
)

# 3. Equip the agent with the file operation tool
#
# NOTE: langgraph.prebuilt.create_react_agent is deprecated as of LangGraph v1
# in favor of langchain.agents.create_agent (same underlying ReAct loop, plus
# a middleware system). The `prompt=` kwarg also becomes `system_prompt=`.
memory_agent = create_agent(
    llm,
    tools = [save_report],
    system_prompt = memory_system_message
)

def run_memory(state: dict) -> dict:
    """Formats the final data and writes it to the local disk."""
    print("\n [Memory] Compiling and saving the final report...")

    # Run the agent to format the text and call the save tool
    result = memory_agent.invoke({"messages": state["messages"]})

    # Isolate only the new messages generated during this turn to append to state.
    # This assumes result["messages"] == state["messages"] + [new stuff], which
    # holds for create_agent's current message-passing behavior -- worth a quick
    # sanity check (e.g. a print of len(result["messages"]) vs len(state["messages"]))
    # if you upgrade langchain/langgraph and this starts looking off.
    new_messages = result["messages"][len(state["messages"]):]

    return {"messages": new_messages}
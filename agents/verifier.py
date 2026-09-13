import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

# Initialize the auditor LLM with absolute zero creativity
llm = ChatOllama(
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
    temperature = 0.0
)

# Create a strict evaluation prompt
verifier_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are teh Verifier Agent. Evaluate the provided research data against the user's objective\n"
     "If the data completely fulfills the objective, respond with exactly 'PASSED: [Brief explanation]'.\n"
     "If it is missing crucial info, respond with exactly 'FAILED: [What is missing].\n"
     "DO NOT hallucinate. Base your judgment entirely on the extracted data provided.\n"
    ),
    ("human", "Objective: {objective}\n\nExtracted Data:\n{extracted_data}")
])

verifier_chain = verifier_prompt | llm

def run_verifier(state: dict) -> dict:
    """Evaluates the extracted data against the original objective."""
    print("\n [Verifier] Fact-checking the extracted data...")

    # Retrieve the user's original request (the first human message)
    objective = next((m.content for m in state["messages"] if m.type == "human"), "Unknown Objective")

    # Compile all the raw scraped data the Researcher saved
    raw_data = "\n\n".join(state.get("extracted_data",[]))

    if not raw_data:
        response = "FAILED: No data was extracted by the Researcher."
    else:
        # Run the evaluation
        result = verifier_chain.invoke({
            "objective": objective,
            # We enforce a context limit here just in case the scrape was massive
            "extracted_data": raw_data[-20000:]
        })
        response = result.content

    print(f" -> Verdict: {response}")

    # Update the graph state with the outcome flag
    return {
        "messages": [AIMessage(content = f"Verifier Report: {response}")],
        "verification_status": "PASSED" if response.startswith("PASSED") else "FAILED"
    }
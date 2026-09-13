import uuid
from langchain_core.messages import HumanMessage
from graph import app

def main():
    print("Research Agent Initialized.\n")
    print("Type 'exit' or 'quit' to shut down the system.\n")

    # LangGraph uses a configuration thread to track the graph's execution state
    # Add recursion_limit to act as a circuit breaker
    config = {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "recursion_limit": 15
    }

    while True:
        user_input = input("[You]: ")

        if user_input.lower() in ['exit', 'quit']:
            print("Shutting down...")
            break

        if not user_input.strip():
            continue

        # 1. Initialize the starting state dictionary
        initial_state = {
            "messages": [HumanMessage(content = user_input)],
            "next_agent": "Supervisor", # Always start by assuming the supervisor handles it
            "extracted_data": [],
            "verification_status": None
        }

        print("\n" + "="*50)
        print("Executing Multi-Agent Workflow...")
        print("="*50)

        # 2. Stream the graph execution
        # By streaming, we allow the print() statements inside our agent nodes to show up in real-time

        try:
            for event in app.stream(initial_state, config = config):
                #The nodes themselves handle the print logs, so we just let the stream flow
                pass

            print("\n Workflow Complete. Check your directory for any saved reports")

        except Exception as e:
            print(f"\n A critical error occurred in the graph: {str(e)}")

if __name__ == "__main__":
    main()

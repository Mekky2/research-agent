from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import ResearchGraphState

# Import our agent nodes
from agents.supervisor import run_supervisor
from agents.researcher import run_researcher
from agents.verifier import run_verifier
from agents.memory import run_memory

# How many consecutive search failures we tolerate before forcing a stop,
# regardless of what the Supervisor LLM decides to do next.
MAX_SEARCH_FAILURES = 3

def route_supervisor(state: ResearchGraphState) -> str:
    """Reads the supervisor's routing decision and maps it to a graph node."""

    # Hard, code-level circuit breaker. The Researcher's messages *tell* the
    # Supervisor to route to FINISH after a failed search, but that's just a
    # hint in free text -- the LLM can (and did, in practice) ignore it and
    # keep retrying the same failing search until recursion_limit crashes the
    # graph. This check doesn't depend on the model cooperating.
    if state.get("search_failures", 0) >= MAX_SEARCH_FAILURES:
        return END

    next_node = state.get("next_agent", "FINISH")

    # If the supervisor decides the job is done, route to the built-in END node
    if next_node == "FINISH":
        return END

    return next_node

# 1. Initialize the graph with our custom shared state
builder = StateGraph(ResearchGraphState)

# 2. Add all the agent nodes
builder.add_node("Supervisor", run_supervisor)
builder.add_node("Researcher", run_researcher)
builder.add_node("Verifier", run_verifier)
builder.add_node("Memory", run_memory)

# 3. Define the hub-and-spoke routing logic
# Every new request always starts at the Supervisor
builder.add_edge(START, "Supervisor")

# The Supervisor conditionally routes to the worker based on its Pydantic output
builder.add_conditional_edges(
    "Supervisor",
    route_supervisor,
    {
        "Researcher": "Researcher",
        "Verifier": "Verifier",
        "Memory": "Memory",
        END: END
    }
)

# After any worker finishes their task, they MUST hand control back to the Supervisor
builder.add_edge("Researcher", "Supervisor")
builder.add_edge("Verifier", "Supervisor")
builder.add_edge("Memory", "Supervisor")

# 4. Compile the graph into a runnable application.
#
# A checkpointer is what makes `thread_id` in main.py's config actually do
# something. Without one, LangGraph has nowhere to persist state between
# invocations, so every call to app.stream() starts from a blank slate
# regardless of what thread_id you pass. MemorySaver keeps checkpoints
# in-process (lost on restart) -- swap in SqliteSaver/PostgresSaver for
# anything that needs to survive a restart.
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)
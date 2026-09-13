import operator
from typing import TypedDict, Annotated, Sequence, List, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class ResearchGraphState(TypedDict):
    """The shared memory clipboard passed between all agents in the graph."""
    # Tracks the conversation history. operator.add ensures we append new messages, not overwrite them.
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # The routing variable the Supervisor uses to direct traffic
    next_agent: str

    # Isolated state variable to store data without clogging the main LLM context window.
    extracted_data: List[str]
    verification_status: Optional[str]

    # Consecutive Wikipedia search failures. Used as a deterministic circuit
    # breaker in graph.py's route_supervisor -- the Supervisor LLM sometimes
    # ignores a "stop the workflow" hint in a text message and keeps retrying
    # the same failing search until the recursion limit crashes the graph.
    # This counter forces a stop in code instead of trusting the model to comply.
    search_failures: int

class SupervisorDecision(BaseModel):
    """The Pydantic guardrail that forces the LLM to output valid JSON routing."""

    next_agent: str = Field(
        description = "The next agent to route to. MUST be one of: 'Researcher', 'Verifier', 'Memory', 'FINISH'."
    )
    instructions: str = Field(
        description = "Highly specific instructions telling the selected agent exactly what to do next based on the current state."
    )
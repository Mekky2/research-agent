from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Fact(BaseModel):
    source_url: str = Field(description="The URL where this information was found")
    fact_summary: str = Field(description="A concise summary of the data extracted")
    confidence: Literal["high", "medium", "low"] = Field(description="Agent's confidence in this fact")

class AgentAction(BaseModel):
    tool_name: Literal["execute_web_search", "scrape_and_extract", "evaluate_findings", "finish"]
    tool_arguments: dict = Field(description="The JSON arguments required for the chosen tool")
    reasoning: str = Field(description="A brief explanation of why this tool was chosen")

class ResearchState(BaseModel):
    objective: str = Field(description="The user's original research request")
    
    # Tracking Progress
    plan: List[str] = Field(default_factory=list, description="Step-by-step research plan")
    current_status: Literal["planning", "researching", "synthesizing", "complete", "error"] = "planning"
    
    # Working Memory
    search_queries_run: List[str] = Field(default_factory=list, description="Queries already searched")
    visited_urls: List[str] = Field(default_factory=list, description="URLs already scraped")
    collected_facts: List[Fact] = Field(default_factory=list, description="Validated data points")
    
    # Next Action Pointer
    next_action: Optional[AgentAction] = None
    
    # Final Output
    draft_report: str = ""
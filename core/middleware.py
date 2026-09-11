import json
import httpx
from core.state import AgentAction, ResearchState

class LLMMiddleware:
    def __init__(self, model_name: str = "qwen2.5-coder:3b"):
        self.api_url = "http://localhost:11434/api/chat"
        self.model_name = model_name

    def decide_next_action(self, state: ResearchState) -> AgentAction:
        """
        Sends the current state to the local LLM and returns a strictly validated action.
        """
        # 1. The System Prompt (Forcing the JSON Schema)
        schema = AgentAction.model_json_schema()
        system_prompt = f"""You are an autonomous research agent.
        Your objective is to complete the research task efficiently.

        RULES:
        1. Search queries must be concise keywords (2 to 4 words, e.g., 'Intel Core Ultra', 'Meteor Lake').
        2. Once URLs are returned, your NEXT action MUST be 'scrape_and_extract' using one of the URLs provided.
        3. Once data is scraped, summarize the findings and call 'finish'.

        You MUST respond in strict JSON format matching exactly this schema:
        {json.dumps(schema, indent=2)}
        """

        # 2. The User Prompt (Passing the current State)
        user_prompt = f"Current State: {state.model_dump_json(indent=2)}\nWhat is your next action?"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",        # Forces Ollama to only output valid JSON
            "stream": False,
            "options": {
                "temperature": 0.1,  # Keep it highly deterministic and logical
                "num_ctx": 4096      # Ensure enough context window for our state
            }
        }

        # 3. Execution & Strict Validation
        try:
            # We use a longer timeout because the 3B model might take a moment on a laptop
            response = httpx.post(self.api_url, json=payload, timeout=120.0)
            response.raise_for_status()
            
            raw_output = response.json()["message"]["content"]
            
            # This is the magic: Pydantic parses the string. If a required field 
            # is missing or types are wrong, this line throws a validation error!
            validated_action = AgentAction.model_validate_json(raw_output)
            return validated_action

        except Exception as e:
            # If the model fails or hallucinates, the middleware catches it safely
            print(f"\n[Middleware Error] Validation failed: {e}")
            
            # Return a safe fallback action to prevent total system crash
            return AgentAction(
                tool_name="evaluate_findings",
                tool_arguments={"error": str(e)},
                reasoning="Middleware intercepted a hallucinated or malformed LLM response."
            )
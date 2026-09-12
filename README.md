A Python-based, locally hosted AI research agent that autonomously plans, searches, scrapes, and synthesizes web data. 

## Features
- **Local AI Engine**: Powered by `qwen2.5-coder:3b` via Ollama for private, zero-cost reasoning.
- **Autonomous Web Research**: Connects to the Wikipedia REST API with compliant bot headers to bypass 403 Forbidden blocks.
- **Smart Scraper**: Extracts clean text using `BeautifulSoup` and `httpx`, aggressively bounded to protect context windows.
- **State Machine Architecture**: Managed via Pydantic to track visited URLs, prevent duplicate actions, and break infinite agent "death loops".

## Setup
1. Create and activate a virtual environment:
   `python3 -m venv venv`
   `source venv/bin/activate`
2. Install dependencies:
   `pip install -r requirements.txt`
3. Ensure Ollama is running with the required model locally.

## Usage
```bash
python3 engine.py


System Architecture

                        [ User Request ]
                              │
                              ▼
                 +--------------------------+
                 |                          |
                 |     Supervisor Agent     | 
                 |  (Orchestrator/Router)   |
                 |                          |
                 +--------------------------+
                   /          │           \
                  /           │            \
                 ▼            ▼             ▼
       +------------+   +------------+   +------------+
       |            |   |            |   |            |
       | Researcher |   |  Verifier  |   |   Memory   |
       |   Agent    |   |   Agent    |   |   Agent    |
       |            |   |            |   |            |
       +------------+   +------------+   +------------+
         [Tools:]         [Tools:]         [Tools:]
         - Search         - Evaluate       - Write File
         - Scrape         - Cross-Check    - Log State
                  \           │            /
                   \          │           /
                    ▼         ▼          ▼
                 +--------------------------+
                 |                          |
                 |    Shared Graph State    |
                 |   (Messages & Context)   |
                 |                          |
                 +--------------------------+
                              │
                              ▼
                   [ Supervisor Decision ]
                  (Route to Agent or FINISH)
      
## Execution Sequence

To prevent the AI from confusing itself (hallucinations), LangGraph uses a strict turn-based system.
Here is the sequence of events when you trigger a new research objective:

### Step 1: State Initialization:

You submit a prompt, LangGraph initialize a **Shared Graph State** and appends your prompt to the message history.

### Step 2: Supervisor Triage (The Guardrail):

The Supervisor Agent wakes up and reads the state. Because we force a strict "with_structured_output" Pydantic guardrail, the LLM is physically forced to output a JSON object containing only 2 things:

1. next_agent (Who to call)
2. instruction (What they need to do)

It recognizes it needs data, so it routes execution to the **Research Agent**.

### Step 3: Execution & Middleware (Researcher Turn):

Control shits to the Researcher Agent.

- It receives the specific instructions from the Supervisor.
- It uses the `execute_web_search` and `scrape_and_extract` tools.
- Middleware kicks in here: if a tool fails (403 Forbidden error or timeout), your middleware catches it, intercept the error, and forces a retry or sanitizes the output before the LLM sees it.
- Once the data is scraped, the Researcher writes its findings back to the *Shared Graph State* and returns control to the Supervisor.

### Step 4: The Evaluation Check (Verifier Turn):

The Supervisor activates again, sees the new data in the state, then decides it needs fact checking. It routes control to the Verifier Agent.

- The Verifier runs in an isolated context (it doesn't care how hard the Researcher worked).
- It cross-references the scraped data against your original objective.
- If the data is garbage, the verifier writes "Failed: Missing NPU specs" to the state. The Supervisor would then route back to the Researcher to try again.
- If the state is good, the Verifier writes "Passed" to the state and hands control back.

### Step 5: Persistence (Memory Turn):

The Supervisor sees the "Passed" flag. before finishing, it routes to the Memory Agent. The Memory Agent uses its file-writing tools to save the final report to your local disk and logs any specific constraints you mentioned for future runs. It updates the state and hands control back.

### Step 6: Graph Termination:

The Supervisor evaluate the state one last time. Seeing that the research is done, verified, and saved, it's output the command "FINISH". LangGraph routes the workflow to the "END" node, effectively shutting down the loop and returning the final compiled response to you.
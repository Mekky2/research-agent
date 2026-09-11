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

=====================================================================
                      THE COGNITIVE LOOP
=====================================================================

  +-------------------------------------------------------------+
  |                        ENGINE (main.py)                     |
  |  Manages the while-loop and holds the current state.        |
  +-----------------------------+-------------------------------+
                                |
                                | 1. Passes ResearchState
                                v
  +-------------------------------------------------------------+
  |                     LLM MIDDLEWARE                          |
  |  +-------------------------------------------------------+  |
  |  | 2. Formats prompt & appends JSON schema               |  |
  |  | 3. POST request to http://localhost:11434/api/chat  -----> [ OLLAMA SERVER ]
  |  | 4. Receives raw string from Qwen-2.5-Coder:3b       <----- [ (Local CPU)   ]
  |  | 5. Pydantic validates raw string into AgentAction     |  |
  |  +-------------------------------------------------------+  |
  +-----------------------------+-------------------------------+
                                |
                                | 6. Returns validated AgentAction
                                v
  +-------------------------------------------------------------+
  |                      TOOL ROUTER                            |
  |  Reads action.tool_name and executes the matching script.   |
  +-----------------------------+-------------------------------+
                                |
           +--------------------+--------------------+
           |                    |                    |
           v                    v                    v
  +-----------------+  +-----------------+  +-------------------+
  |   search.py     |  |   scraper.py    |  | evaluate_findings |
  | (DuckDuckGo API)|  | (BeautifulSoup) |  | (Checks goal)     |
  +--------+--------+  +--------+--------+  +--------+----------+
           |                    |                    |
           +--------------------+--------------------+
                                |
                                | 7. Tool returns data (Facts, URLs)
                                v
  +-------------------------------------------------------------+
  |                      STATE UPDATE                           |
  |  Appends new facts to ResearchState.collected_facts.        |
  |  Updates visited_urls and search_queries_run.               |
  +-------------------------------------------------------------+
                                |
                                | 8. Loop repeats until complete
                                \_________________________________ (Back to Top)


                                # Autonomous Local AI Research Agent


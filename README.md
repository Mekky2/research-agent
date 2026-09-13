# Research Agent

A locally hosted, multi-agent AI research assistant built on LangGraph. It plans, searches Wikipedia, scrapes and verifies the results, and saves a synthesized report to disk — all running against a local Ollama model, with no cloud API calls.

## Features

- **Local AI engine** — runs entirely through [Ollama](https://ollama.com), so reasoning is private and has no per-token cost. Defaults to `qwen3:8b`; configurable via `.env`.
- **Autonomous web research** — searches Wikipedia's API with a policy-compliant identity header, falling back through full-text search, title-prefix matching, and query simplification if an exact phrase comes up empty.
- **Resilient by design** — a hard, code-level circuit breaker halts the workflow after repeated consecutive search failures, rather than relying on the model to notice and stop on its own.
- **Fact-checked output** — a dedicated Verifier agent cross-checks scraped data against your original question before anything gets written to disk.
- **Multi-turn memory** — conversation history persists across turns within a session via LangGraph's checkpointer, so follow-up questions have context from earlier in the same run.

## Setup

1. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Start Ollama and pull a model**
   ```bash
   ollama pull qwen3:8b
   ```
4. **Configure your `.env`**

   | Variable | Purpose | Example |
   |---|---|---|
   | `OLLAMA_MODEL` | Local model to use for all agents | `qwen3:8b` |
   | `OLLAMA_BASE_URL` | Where Ollama is running | `http://localhost:11434` |
   | `USER_AGENT` | Identity sent to Wikipedia and scraped sites — **must include real contact info** or requests get a 403 | `ResearchAgentBot/1.0 (you@example.com)` |
   | `MAX_ROUTING_STEPS` | Recursion limit — max Supervisor↔worker handoffs before a run aborts | `20` |
   | `SCRAPE_CHAR_LIMIT` | Max characters kept per scraped page | `10000` |

   Keep `.env` out of version control (see `.gitignore`) — it's meant to hold your personal contact info, not something to publish.

## Usage

```bash
python3 main.py
```

Type your research question at the `[You]:` prompt. Type `exit` or `quit` to shut down.

## Architecture

```
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
         [Tools:]         [Checks:]        [Tools:]
         - Search         - Cross-check    - Write file
         - Scrape           vs. objective

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
```

Every worker hands control back to the Supervisor after finishing — the Supervisor is the only node that decides what happens next, based on a Pydantic-constrained structured output (`next_agent` + `instructions`). Everything else in the graph (messages, extracted data, verification status) lives in a shared `TypedDict` state, not a Pydantic model — Pydantic is only used to force the Supervisor's and Researcher's *decisions* into valid, parseable JSON.

## Execution sequence

1. **State initialization** — your prompt is added to the shared message history. Per-turn scratch fields (`extracted_data`, `verification_status`, `search_failures`) reset; the message history itself persists across turns in the same session.

2. **Supervisor triage** — the Supervisor reads the current state and, constrained by a Pydantic schema, outputs exactly two fields: `next_agent` (who acts next) and `instructions` (what they should do). On a fresh question with no data yet, it routes to the **Researcher**.

3. **Researcher turn** — the Researcher follows the Supervisor's instructions, using `execute_web_search` and `scrape_and_extract`. If a search fails (a 403, a timeout, or genuinely no results), the tool itself already tried several fallback strategies before giving up, and reports back *why* it failed rather than failing silently. Three consecutive failures trip the circuit breaker and the graph ends immediately, regardless of what the Supervisor would otherwise decide. On success, findings are appended to the shared state and control returns to the Supervisor.

4. **Verifier turn** — once data exists, the Supervisor routes to the Verifier, which checks the scraped data against your original objective in isolation (it has no visibility into how the Researcher got there). It writes either `PASSED: ...` or `FAILED: ...` to the state. A `FAILED` result sends the Supervisor back to the Researcher for another attempt.

5. **Memory turn** — once verification passes, the Supervisor routes to the Memory agent, which formats the verified findings into a report and writes it to disk with the `save_report` tool.

6. **Termination** — with the report saved and verification passed, the Supervisor outputs `FINISH`, LangGraph routes to `END`, and the run completes.

## Folder structure

```
research-agent/
├── .env                  # Environment variables (gitignored — see Setup)
├── .gitignore
├── requirements.txt       # Python dependencies
├── state.py               # Shared graph state (TypedDict) + Pydantic decision schemas
├── main.py                # Entry point — the CLI loop
├── graph.py                # Wires agents + state into the compiled LangGraph app
├── tools/
│   ├── __init__.py
│   ├── search.py          # Wikipedia search tool (with fallback strategies)
│   ├── scraper.py         # Generic URL text-extraction tool
│   └── file_ops.py        # File-saving tool used by the Memory agent
└── agents/
    ├── __init__.py
    ├── supervisor.py      # Router — decides which agent acts next
    ├── researcher.py       # Executes search + scrape tools
    ├── verifier.py          # Fact-checks extracted data against the objective
    └── memory.py            # Formats and saves the final report
```

## Notes & limitations

- Research is currently limited to Wikipedia — good for grounded, encyclopedic facts, less useful for anything requiring very recent news or non-encyclopedic sources.
- Everything runs on whatever local model you configure; smaller models may occasionally ignore the Supervisor's routing instructions, which is exactly what the circuit breaker in `graph.py` is there to catch.
- `MemorySaver` (LangGraph's in-memory checkpointer) is used by default, so conversation history resets when the process restarts. Swap in `SqliteSaver` or `PostgresSaver` if you need it to survive restarts.
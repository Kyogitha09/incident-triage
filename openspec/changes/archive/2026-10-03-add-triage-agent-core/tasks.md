# Tasks

## 1. Connection Pool & Tooling Setup

- [x] 1.1 Implement `get_db_pool()` in `agent.py` using `psycopg_pool.ConnectionPool` with `autocommit=True`, `connect_timeout=15`, and `prepare_threshold=None` for Supabase transaction pooler compatibility
- [x] 1.2 Implement `query_service_health(service_name: str)` tool with mock catalog (`auth`, `payments`, `database`) and graceful not-found handling for unknown services
- [x] 1.3 Implement `search_remediation_runbooks(query: str, service: str = None)` tool using `genai.Client` embeddings (768 dims) and SQL function `match_incident_docs` returning top 2 matches or fallback message
- [x] 1.4 Implement `extract_text` helper function to flatten string or list/dict-structured message content into a plain string

## 2. LangGraph Core Agent & Checkpointer

- [x] 2.1 Define `AgentState` schema and system prompt instructing health-first triage before runbook search
- [x] 2.2 Construct the LangGraph workflow: `agent` -> `safe_tools` -> `agent` loop, routing to `END` when no tool calls exist
- [x] 2.3 Implement `get_agent_app()` with `PostgresSaver` checkpointer calling `checkpointer.setup()` and returning the compiled graph

## 3. Testing & Verification

- [x] 3.1 Create `tests/test_agent.py` with mocked LLM tool calls and verify health-first tool routing and unknown service handling
- [x] 3.2 Add test in `tests/test_agent.py` verifying state persistence survives a simulated process restart for the same `thread_id`
- [x] 3.3 Run `pytest -q` to verify all unit tests pass
- [x] 3.4 Execute an end-to-end smoke test against the live agent using `get_agent_app().invoke()` with a test thread ID

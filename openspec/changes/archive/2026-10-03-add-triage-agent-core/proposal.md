# Proposal

## Why

Incident response requires quick triage: determining service health status and locating relevant runbooks without human delay. This change establishes the core LangGraph-powered triage agent with safe, read-only tools and transactional conversation persistence.

## What Changes

- Implement `agent.py` containing the core LangGraph incident triage graph:
  - Connection management using `psycopg_pool.ConnectionPool` configured specifically for Supabase's transaction pooler (port 6543, `prepare_threshold=None`).
  - Read-only tools: `query_service_health` (mock service table) and `search_remediation_runbooks` (vector search over `incident_docs` via RPC `match_incident_docs`, returning top 2 matches).
  - Graph architecture: `agent` -> `safe_tools` -> `agent` loop, terminating at `END` when the model decides no further tools are needed.
  - State persistence using `PostgresSaver` with table setup (`setup()`), persisting conversation history per `thread_id`.
  - Content normalisation helper `extract_text` ensuring model list/block outputs are converted cleanly into plain strings.
  - Graph factory function `get_agent_app()`.
- Add unit tests verifying routing, safe tool execution, and state persistence across process restarts using mocked LLMs and DB connections.

## Capabilities

### New Capabilities
- `triage-agent`: Autonomous investigation of service degradation using safe health queries and runbook search, with thread-level state persistence.

### Modified Capabilities
- (None)

## Impact

- **Affected Code**: Creates `agent.py` and `tests/test_agent.py`.
- **Database**: `PostgresSaver.setup()` initializes checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) in Supabase Postgres.
- **Rollback Note**: Revert `agent.py` and `tests/test_agent.py`. Checkpoint tables in Supabase can remain or be dropped via SQL Editor.

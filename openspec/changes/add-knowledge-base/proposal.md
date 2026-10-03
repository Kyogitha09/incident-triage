# Proposal

## Why

To support the Autonomous Incident Triage Agent, we need a vectorized knowledge base to store and retrieve incident runbooks. This enables the agent to autonomously search for matching remediation steps based on an incident description.

## What Changes

- Create a SQL migration `db/migrations/001_incident_docs.sql` to enable `pgvector`, create the `incident_docs` table (content, jsonb metadata, 768-dim embedding), and add a `match_incident_docs` RPC function (cosine similarity, match_count, metadata filter).
- Create a `requirements.txt` with necessary project dependencies (gradio, fastapi, uvicorn, langgraph, langgraph-checkpoint-postgres, langchain-google-genai, langchain-core, psycopg[binary,pool], python-dotenv, pydantic, pytest).
- Implement `seed_rag.py` to embed three sample runbooks (auth 504 timeouts, database high latency, payment gateway failures) using Gemini embeddings (`task_type=RETRIEVAL_DOCUMENT`, 768 dims) and insert them via the Supabase pooler.
- Ensure seeding is idempotent so re-running does not create duplicates.
- Add unit tests mocking the embeddings client and DB connection.

## Capabilities

### New Capabilities
- `knowledge-base`: Storing, embedding, and querying incident runbooks using `pgvector` and Gemini embeddings.

### Modified Capabilities
- (None)

## Impact

- **Database**: Adds the `pgvector` extension, a new table (`incident_docs`), and a new RPC function (`match_incident_docs`) to the Supabase instance.
- **Dependencies**: Introduces the core Python requirements for the project.
- **Rollback Note**: To rollback, drop the `incident_docs` table and `match_incident_docs` function via the Supabase SQL Editor, and revert any dependency installations.

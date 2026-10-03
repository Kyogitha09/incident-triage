# Design

## Context

We are introducing the foundational data layer for the triage agent: a vector store to hold incident runbooks. This leverages Supabase with pgvector and Gemini embeddings.

## Goals / Non-Goals

**Goals:**
- Enable vector search on runbooks.
- Automate DB migrations and idempotently seed initial data.

**Non-Goals:**
- Automated extraction or ingestion of runbooks from Notion/Confluence (using a static list for now).
- Vectorizing past incidents (only runbooks are stored for now).

## Decisions

- **Database Extension**: We use `pgvector` inside Supabase. *Alternative*: Dedicated vector DB like Pinecone. We chose Supabase because it also provides relational storage for LangGraph state later, keeping our stack zero-cost and consolidated.
- **Embeddings Model**: `text-embedding-004` (Gemini via Google AI Studio). *Alternative*: OpenAI embeddings. Gemini is used to stay within the free-tier Google AI Studio offering.
- **Connection Management**: `psycopg_pool` is used for the database connection.
- **RPC Search Function**: We use a custom PL/pgSQL function (`match_incident_docs`) for similarity search to easily allow filtering and limit configuration directly within the DB layer.

## Risks / Trade-offs

- [Supabase Transaction Pooler Quirks] → The pooler on port 6543 doesn't maintain prepared statements across transactions. Mitigation: For any `psycopg_pool` initialization, we will ensure it is configured appropriately (e.g., `prepare_threshold=None`).
- [Google AI Studio Rate Limits] → Free tier RPM limits. Mitigation: Seeding only 3 runbooks won't hit limits, but if we expand, we will need backoff/retry logic.
- [Render Cold Starts] → Web services sleep after 15 minutes. Mitigation: Not an issue for seeding, but we must keep it in mind for the eventual API design.

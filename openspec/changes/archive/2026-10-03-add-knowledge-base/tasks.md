# Tasks

## 1. Database Migration

- [ ] 1.1 Create `db/migrations/001_incident_docs.sql` with `CREATE EXTENSION IF NOT EXISTS vector`, the `incident_docs` table (id, content TEXT, metadata JSONB, embedding vector(768), content_hash TEXT UNIQUE), and the `match_incident_docs` PL/pgSQL function using cosine similarity. Verify by opening the file and confirming all three SQL blocks are present.
- [ ] 1.2 Run the migration manually in the Supabase SQL Editor. Verify by querying `SELECT * FROM incident_docs LIMIT 1;` without error.

## 2. Python Dependencies

- [ ] 2.1 Create `requirements.txt` containing: `fastapi`, `uvicorn`, `gradio`, `langgraph`, `langgraph-checkpoint-postgres`, `langchain-google-genai`, `langchain-core`, `psycopg[binary,pool]`, `python-dotenv`, `pydantic`, `pytest`. Verify by running `pip install -r requirements.txt` in the `.venv` and confirming no errors.

## 3. Seeding Script

- [ ] 3.1 Create `seed_rag.py` that loads `GEMINI_API_KEY` and `DATABASE_URL` from environment variables via `python-dotenv`. Verify the script exits with a clear error if either variable is missing.
- [ ] 3.2 Add three runbook entries as Python dicts (auth 504 timeouts, database high latency, payment gateway failures). Verify by inspecting the variable in the source.
- [ ] 3.3 Implement idempotent insertion: compute `content_hash = md5(content)`, `SELECT` from `incident_docs` before inserting, skip if found. Verify by running `seed_rag.py` twice and checking that only 3 rows exist in the table.
- [ ] 3.4 Embed each runbook using `GoogleGenerativeAIEmbeddings(model="text-embedding-004", task_type="RETRIEVAL_DOCUMENT")` with `output_dimensionality=768`. Verify embeddings are 768-dimensional before insert (assert `len(embedding) == 768`).
- [ ] 3.5 Connect to Supabase via `psycopg_pool.ConnectionPool` with `kwargs={"prepare_threshold": None}` to avoid prepared-statement errors through the transaction pooler. Verify the pool opens without error on startup.

## 4. Unit Tests

- [ ] 4.1 Create `tests/test_seed_rag.py`. Mock `GoogleGenerativeAIEmbeddings.embed_query` to return a fixed 768-dim list. Mock `psycopg_pool.ConnectionPool` and its cursor. Verify these mocks are in place before any test runs.
- [ ] 4.2 Write test `test_seed_inserts_new_runbook`: given no existing rows, assert `INSERT` is called three times. Verify by running `pytest tests/test_seed_rag.py::test_seed_inserts_new_runbook`.
- [ ] 4.3 Write test `test_seed_skips_existing_runbook`: given existing `content_hash` rows, assert `INSERT` is never called. Verify by running `pytest tests/test_seed_rag.py::test_seed_skips_existing_runbook`.
- [ ] 4.4 Run the full test suite with `pytest tests/` and confirm all tests pass.

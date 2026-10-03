# Autonomous Incident Triage Agent

An autonomous incident response system built with LangGraph, Google Gemini, and Supabase pgvector with Human-in-the-Loop (HITL) approval.

## Features
- **Health-First Triage**: Checks affected service status before searching runbooks.
- **RAG Remediation**: Semantic search over incident runbooks with 768-dim embeddings (`gemini-embedding-001`).
- **Human-in-the-Loop**: Escalation pauses for explicit engineer approval before creating tickets or paging teams.
- **Persistent State**: Checkpointed in Supabase PostgreSQL across worker restarts.
- **Web UI & REST API**: Dual-access via Gradio Blocks and FastAPI endpoints (`/chat`, `/approve`, `/healthz`).

## Local Development
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Configure `.env`:
   ```
   GEMINI_API_KEY="your-gemini-key"
   DATABASE_URL="your-supabase-transaction-pooler-url"
   ```
3. Run tests:
   ```powershell
   pytest -q
   ```
4. Start the server:
   ```powershell
   python app.py
   ```
   Open `http://localhost:7860` in your browser.

## Deployment to Render
1. Push this repository to GitHub.
2. In Render, select **New -> Blueprint** and point to your repository (or **New -> Web Service** using `render.yaml`).
3. Set environment variables in the Render dashboard:
   - `GEMINI_API_KEY`: Google AI Studio API key
   - `DATABASE_URL`: Supabase Transaction Pooler URL (port 6543)
4. Free-tier notes:
   - Service spins down after 15 minutes of inactivity.
   - Cold starts take 30–60 seconds, but thread state is fully preserved in Postgres.

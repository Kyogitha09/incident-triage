# Design

## Context

See `proposal.md` for motivation. Builds on Changes 1–4.

## Goals / Non-Goals

**Goals:**
- Provide blueprint `render.yaml` declaring Python 3.11.9, start command with `$PORT`, build command `pip install -r requirements.txt`.
- Keep environment secrets (`GEMINI_API_KEY`, `DATABASE_URL`) explicitly marked `sync: false`.
- Verify `.env` is uncommitted.
- Document deployment steps and free-tier trade-offs in `README.md`.

## Decisions

- **Decision 1: Use Render blueprint specification (`render.yaml`)**
  - *Rationale*: Reproducible deployment with 1-click Render blueprint creation.

## Risks / Trade-offs

- **[Risk: 15-minute inactivity spin down]** → Cold start of 30-60 seconds on free tier. *Mitigation*: State persists safely in Supabase PostgreSQL checkpointer across restarts.

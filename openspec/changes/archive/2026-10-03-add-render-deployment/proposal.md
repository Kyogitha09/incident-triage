# Proposal

## Why

To make the Autonomous Incident Triage Agent accessible as a live, always-on service without infrastructure cost, it must be deployable to Render's free tier.

## What Changes

- Add `render.yaml` configuration declaring a free web service running `uvicorn app:app --host 0.0.0.0 --port $PORT` with Python 3.11.9.
- Ensure `GET /healthz` endpoint responds with 200 without calling external services.
- Provide README section with Render deployment instructions and free-tier operational notes (15-min spin down, cold starts).
- Verify git tracking ensures `.env` is never committed.

## Capabilities

### New Capabilities
- `deployment`: Live cloud deployment specification on Render free tier.

### Modified Capabilities
- (None)

## Impact

- **Affected Files**: `render.yaml`, `README.md`.
- **Rollback Note**: Delete `render.yaml`.

# Tasks

## 1. Service Layer & FastAPI Application

- [x] 1.1 Implement core service helper functions (`process_chat`, `process_approval`) shared by REST and UI
- [x] 1.2 Implement FastAPI routes `POST /chat`, `POST /approve`, and `GET /healthz`
- [x] 1.3 Implement Gradio Blocks interface mounted at `"/"`
- [x] 1.4 Add `if __name__ == "__main__":` entrypoint with `uvicorn.run()` on port `$PORT` (default 7860)

## 2. Testing & Verification

- [x] 2.1 Create `tests/test_api.py` with FastAPI TestClient testing `/chat`, `/approve` (200 and 400), and `/healthz`
- [x] 2.2 Run `pytest -q` to verify all tests pass

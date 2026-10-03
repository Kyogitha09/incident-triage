import os
import json
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from psycopg_pool import ConnectionPool

load_dotenv()

RUNBOOKS = [
    {"service": "auth", "content": "Auth service 504 timeouts. Check Redis cache and token refresh endpoint. Restart auth pods if needed."},
    {"service": "database", "content": "Database high latency. Check pg_stat_activity for long running queries. Verify connection pool limits."},
    {"service": "payments", "content": "Payment gateway failures. Check third-party API status. Verify webhook signature validation."}
]


def get_embedding(client: genai.Client, text: str) -> list[float]:
    """Embed text using gemini-embedding-001 (768-dim, available on free AI Studio keys)."""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    return result.embeddings[0].values


def seed_runbooks():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return

    # gemini-embedding-001 is available on the default v1beta endpoint
    client = genai.Client(api_key=api_key)
    pool = ConnectionPool(db_url, min_size=1, max_size=2, kwargs={"prepare_threshold": None})

    with pool.connection() as conn:
        with conn.cursor() as cur:
            for rb in RUNBOOKS:
                content = rb["content"]
                content_hash = hashlib.md5(content.encode()).hexdigest()

                # Idempotency check
                cur.execute("SELECT id FROM incident_docs WHERE content_hash = %s", (content_hash,))
                if cur.fetchone():
                    print(f"Skipping {rb['service']} (already exists)")
                    continue

                embedding = get_embedding(client, content)
                assert len(embedding) == 768, f"Expected 768 dims, got {len(embedding)}"
                metadata = json.dumps({"service": rb["service"]})

                cur.execute(
                    "INSERT INTO incident_docs (content, metadata, embedding, content_hash) VALUES (%s, %s, %s, %s)",
                    (content, metadata, embedding, content_hash)
                )
                print(f"Inserted runbook for {rb['service']}")
        conn.commit()
    pool.close()


if __name__ == "__main__":
    seed_runbooks()

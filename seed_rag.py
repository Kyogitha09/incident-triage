import os
import json
import hashlib
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import psycopg
from psycopg_pool import ConnectionPool

load_dotenv()

RUNBOOKS = [
    {"service": "auth", "content": "Auth service 504 timeouts. Check Redis cache and token refresh endpoint. Restart auth pods if needed."},
    {"service": "database", "content": "Database high latency. Check pg_stat_activity for long running queries. Verify connection pool limits."},
    {"service": "payments", "content": "Payment gateway failures. Check third-party API status. Verify webhook signature validation."}
]

def seed_runbooks():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004", 
        task_type="RETRIEVAL_DOCUMENT"
    )
    
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return

    pool = ConnectionPool(db_url, min_size=1, max_size=2, kwargs={"prepare_threshold": None})
    
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for rb in RUNBOOKS:
                content = rb["content"]
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Check if exists (idempotency)
                cur.execute("SELECT id FROM incident_docs WHERE content_hash = %s", (content_hash,))
                if cur.fetchone():
                    print(f"Skipping {rb['service']} (already exists)")
                    continue
                
                embedding = embeddings.embed_query(content)
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

from unittest.mock import MagicMock, patch

FAKE_EMBEDDING = [0.1] * 768  # 768-dim fake vector


def make_mock_pool(existing_hash=None):
    """Return a mock ConnectionPool whose cursor behaves like a real psycopg cursor."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (1,) if existing_hash else None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cur
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.connection.return_value.__enter__ = lambda s: mock_conn
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)

    return mock_pool, mock_cur


def make_mock_client():
    """Return a mock genai.Client whose embed_content returns a 768-dim embedding."""
    mock_embedding = MagicMock()
    mock_embedding.values = FAKE_EMBEDDING

    mock_result = MagicMock()
    mock_result.embeddings = [mock_embedding]

    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_result
    return mock_client


@patch("seed_rag.ConnectionPool")
@patch("seed_rag.genai")
def test_seed_inserts_new_runbooks(mock_genai, mock_pool_cls):
    """When no runbooks exist, INSERT is called once per runbook (3 total)."""
    mock_genai.Client.return_value = make_mock_client()
    mock_pool, mock_cur = make_mock_pool(existing_hash=None)
    mock_pool_cls.return_value = mock_pool

    from seed_rag import seed_runbooks
    seed_runbooks()

    # 3 runbooks → 3 SELECT checks + 3 INSERTs
    assert mock_cur.execute.call_count == 6
    insert_calls = [c for c in mock_cur.execute.call_args_list
                    if "INSERT" in str(c)]
    assert len(insert_calls) == 3


@patch("seed_rag.ConnectionPool")
@patch("seed_rag.genai")
def test_seed_skips_existing_runbooks(mock_genai, mock_pool_cls):
    """When all runbooks already exist, INSERT is never called."""
    mock_genai.Client.return_value = make_mock_client()
    mock_pool, mock_cur = make_mock_pool(existing_hash="exists")
    mock_pool_cls.return_value = mock_pool

    from seed_rag import seed_runbooks
    seed_runbooks()

    # Only 3 SELECT checks — no INSERTs
    insert_calls = [c for c in mock_cur.execute.call_args_list
                    if "INSERT" in str(c)]
    assert len(insert_calls) == 0

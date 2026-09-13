import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from nexus_connectors.postgres.connector import PostgresConnector

CREDS = {"host": "localhost", "database": "testdb", "username": "admin", "password": "secret", "ssl_mode": "disable"}


@pytest.mark.asyncio
async def test_execute_query():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    with patch("asyncpg.connect", return_value=mock_conn):
        c = PostgresConnector(credentials=CREDS)
        result = await c.execute_action("execute_query", {"query": "SELECT * FROM users"})

    assert result["row_count"] == 2
    assert result["rows"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_execute_statement():
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "UPDATE 3"

    with patch("asyncpg.connect", return_value=mock_conn):
        c = PostgresConnector(credentials=CREDS)
        result = await c.execute_action("execute_statement", {"statement": "UPDATE users SET active=true"})

    assert result["affected_rows"] == 3

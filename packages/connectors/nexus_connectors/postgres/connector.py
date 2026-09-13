from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_sdk import Connector, ConnectorError


class PostgresConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _dsn(self) -> str:
        host = self.credentials.get("host", "localhost")
        port = self.credentials.get("port", "5432")
        db = self.credentials.get("database", "")
        user = self.credentials.get("username", "")
        pwd = self.credentials.get("password", "")
        ssl = self.credentials.get("ssl_mode", "require")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={ssl}"

    async def test_connection(self) -> dict[str, Any]:
        import asyncpg
        try:
            conn = await asyncpg.connect(self._dsn())
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return {"ok": True, "version": version}
        except Exception as exc:
            raise ConnectorError(str(exc), retriable=False)

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_execute_query(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import asyncpg
        query = inputs["query"]
        params_raw = inputs.get("params", "[]")
        params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw
        max_rows = int(inputs.get("max_rows", 100))

        try:
            conn = await asyncpg.connect(self._dsn())
            rows = await conn.fetch(query, *params)
            await conn.close()
        except Exception as exc:
            raise ConnectorError(str(exc), retriable=False)

        row_dicts = [dict(r) for r in rows[:max_rows]]
        return {"rows": row_dicts, "row_count": len(row_dicts)}

    async def action_insert_row(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import asyncpg
        table = inputs["table"]
        row: dict[str, Any] = inputs["row"]
        returning = inputs.get("returning", "*")

        cols = list(row.keys())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
        col_list = ", ".join(f'"{c}"' for c in cols)
        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) RETURNING {returning}'

        try:
            conn = await asyncpg.connect(self._dsn())
            result = await conn.fetchrow(sql, *[row[c] for c in cols])
            await conn.close()
        except Exception as exc:
            raise ConnectorError(str(exc), retriable=False)

        return {"inserted_row": dict(result) if result else {}}

    async def action_execute_statement(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import asyncpg
        stmt = inputs["statement"]
        params_raw = inputs.get("params", "[]")
        params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw

        try:
            conn = await asyncpg.connect(self._dsn())
            status = await conn.execute(stmt, *params)
            await conn.close()
        except Exception as exc:
            raise ConnectorError(str(exc), retriable=False)

        # asyncpg returns e.g. "UPDATE 3" — parse the count
        parts = (status or "").split()
        affected = int(parts[-1]) if parts and parts[-1].isdigit() else 0
        return {"affected_rows": affected}

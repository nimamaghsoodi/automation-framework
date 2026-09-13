from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

from nexus_sdk import Connector, ConnectorError


class CodeConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    async def test_connection(self) -> dict[str, Any]:
        return {"ok": True}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if action_key != "run_python":
            raise ConnectorError(f"Unknown action: {action_key!r}")
        return await self._run_python(inputs)

    _INTERNAL_KEYS = frozenset(["source_code", "action_key", "timeout_seconds", "credential_instance_id"])

    @staticmethod
    def _safe_json(obj: Any) -> str:
        """Serialize to JSON with ensure_ascii=True and a str() fallback for non-serializable
        values. The result is guaranteed to contain only ASCII, so no surrogate issues."""
        return json.dumps(obj, ensure_ascii=True, default=str)

    async def _run_python(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import asyncio

        source_code = inputs.get("source_code", "")
        timeout = int(inputs.get("timeout_seconds", 30))

        if not source_code.strip():
            raise ConnectorError("source_code is empty")

        # Strip internal keys — what remains is data from predecessor steps.
        raw_inputs = {k: v for k, v in inputs.items() if k not in self._INTERNAL_KEYS}

        # Round-trip through JSON with ensure_ascii so surrogates from upstream
        # HTTP responses are safely escaped before we embed them in the wrapper.
        try:
            inputs_json = self._safe_json(raw_inputs)
        except Exception:
            inputs_json = "{}"

        # Sanitize source code: replace any surrogates so exec() doesn't choke.
        source_code = source_code.encode("utf-8", errors="replace").decode("utf-8")

        # Build wrapper. Both embedded strings are pure ASCII after the steps above.
        wrapper = textwrap.dedent(f"""\
            import json as _json

            inputs = _json.loads({json.dumps(inputs_json)})

            _user_ns = {{"inputs": inputs}}
            _source = {json.dumps(source_code)}
            exec(_source, _user_ns)

            _output = _user_ns.get("output")
            if _output is None:
                _output = {{}}
            elif not isinstance(_output, dict):
                _output = {{"value": _output}}
            print(_json.dumps(_output, ensure_ascii=True, default=str))
        """)

        # Pass the wrapper via stdin instead of -c to avoid OS command-line
        # length limits and encoding issues with multi-byte characters.
        wrapper_bytes = wrapper.encode("utf-8")

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    sys.executable, "-",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout + 2,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=wrapper_bytes),
                timeout=timeout + 2,
            )
        except asyncio.TimeoutError:
            raise ConnectorError(f"Script timed out after {timeout}s", retriable=False)

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            raise ConnectorError(f"Script error:\n{err_msg}", retriable=False)

        raw = stdout.decode("utf-8", errors="replace").strip()
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {"stdout": raw}

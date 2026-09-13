from __future__ import annotations

import json
import subprocess
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

    async def _run_python(self, inputs: dict[str, Any]) -> dict[str, Any]:
        import asyncio

        source_code = inputs.get("source_code", "")
        timeout = int(inputs.get("timeout_seconds", 30))
        flow_inputs = inputs.get("_flow_inputs", {})    # injected by task runner
        trigger_data = inputs.get("_trigger_data", {})  # injected by task runner

        if not source_code.strip():
            raise ConnectorError("source_code is empty")

        # Build a wrapper that injects variables and captures `output`
        wrapper = textwrap.dedent(f"""\
            import json as _json
            import sys as _sys

            inputs = _json.loads({json.dumps(json.dumps(flow_inputs))})
            trigger = _json.loads({json.dumps(json.dumps(trigger_data))})

            _user_ns = {{"inputs": inputs, "trigger": trigger}}
            _source = {json.dumps(source_code)}
            exec(_source, _user_ns)

            _output = _user_ns.get("output")
            if _output is None:
                _output = {{}}
            elif not isinstance(_output, dict):
                _output = {{"value": _output}}
            print(_json.dumps(_output))
        """)

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    sys.executable, "-c", wrapper,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout + 2,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 2)
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

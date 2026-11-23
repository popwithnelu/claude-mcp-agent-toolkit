"""Minimal MCP-style server over stdio (JSON-RPC 2.0, newline-delimited).

Implements the core MCP handshake and methods — initialize, tools/list,
tools/call — with no external dependencies, so it runs anywhere. It is
wire-compatible with the shapes MCP clients exchange; the official `mcp`
SDK can wrap the same TOOLS registry when installed.

Run: python -m mcp_server.server   (speaks JSON-RPC on stdin/stdout)
"""
import json
import sys

from .tools import TOOLS

PROTOCOL_VERSION = "2024-11-05"


def handle(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "claude-mcp-agent-toolkit", "version": "0.1.0"}}
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": t["description"],
                             "inputSchema": t["input_schema"]} for n, t in TOOLS.items()]}
    elif method == "tools/call":
        params = request.get("params", {})
        tool = TOOLS.get(params.get("name"))
        if tool is None:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": f"unknown tool: {params.get('name')}"}}
        try:
            out = tool["handler"](params.get("arguments", {}))
            result = {"content": [{"type": "text", "text": json.dumps(out)}], "isError": False}
        except Exception as exc:  # tool errors are returned, not raised, per MCP convention
            result = {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.claude_client import ClaudeAgent, validate_structured
from evals.harness import load_cases, run_evals
from mcp_server.server import handle
from mcp_server.tools import TOOLS, calculator, document_search, file_summarizer

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_tools_work():
    assert calculator("2 + 3 * 4") == 14
    assert document_search("model context protocol")[0]["doc_id"] == "mcp-intro"
    summary = file_summarizer(os.path.join(ROOT, "evals", "golden_cases.json"))
    assert summary["word_count"] > 0 and summary["summary"]


def test_calculator_rejects_code():
    try:
        calculator("__import__('os')")
        raise AssertionError("should have raised")
    except Exception:
        pass


def test_mcp_protocol_handlers():
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "claude-mcp-agent-toolkit"
    tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert {t["name"] for t in tools["result"]["tools"]} == set(TOOLS)
    call = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": "calculator", "arguments": {"expression": "10 / 4"}}})
    assert json.loads(call["result"]["content"][0]["text"]) == 2.5


def test_mcp_server_stdio_roundtrip():
    proc = subprocess.run(
        [sys.executable, "-m", "mcp_server.server"],
        input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n',
        capture_output=True, text=True, cwd=ROOT, timeout=30)
    out = json.loads(proc.stdout.strip().splitlines()[0])
    assert out["id"] == 1 and len(out["result"]["tools"]) == 3


def test_mock_agent_and_structured_output():
    agent = ClaudeAgent(TOOLS)
    assert agent.mode == "mock"
    result = agent.run("Calculate: 6 * 7")
    assert "42" in result["answer"] and validate_structured(result)


def test_eval_harness():
    cases = load_cases(os.path.join(ROOT, "evals", "golden_cases.json"))
    report = run_evals(cases)
    assert report["mean"] == 1.0 and report["mode"] == "mock"

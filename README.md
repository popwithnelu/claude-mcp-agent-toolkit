# Claude MCP Agent Toolkit

A hands-on project built around the **Claude API** and the **Model Context
Protocol (MCP)**, aligned with the domains covered by the Claude Certified
Architect program.

## What's inside

| Component | What it demonstrates |
|---|---|
| `mcp_server/` | An MCP-style server over **stdio** (JSON-RPC: `initialize`, `tools/list`, `tools/call`) exposing real tools — document search, a safe calculator, and a file summarizer |
| `agent/claude_client.py` | A Claude agent with a **tool-use loop**, **prompt caching** (`cache_control` on the stable system prompt), and **structured outputs** validated against a JSON schema |
| `evals/` | A small **evaluation harness** scoring agent answers against golden cases |

## Claude Architect domains covered

- **Claude API** — Messages API, model selection, token budgets
- **Tool use / function calling** — tool specs, `tool_use` / `tool_result` loop
- **MCP** — client-server tool protocol, tool discovery, error-as-result convention
- **Agentic workflows** — plan → call tools → observe → answer loop
- **Prompt design** — stable, cacheable system prompts; structured output schemas
- **Evaluation** — golden cases, contains-based scoring, regression-friendly reports

## Offline / mock mode

With no `ANTHROPIC_API_KEY` set, the agent runs against a deterministic mock
that still exercises the tool registry and the eval harness, so everything —
including the tests — runs offline. Set the key (and `pip install anthropic`)
for live Claude calls.

## Run

```bash
pip install -r requirements.txt
python -m mcp_server.server          # MCP server on stdio
python -m pytest                     # offline tests
python -c "from evals.harness import load_cases, run_evals; print(run_evals(load_cases('evals/golden_cases.json')))"
```

## Project structure

```
mcp_server/ (server, tools) · agent/claude_client.py · evals/ (harness, golden_cases.json) · tests/test_toolkit.py
```

MIT License — see LICENSE.

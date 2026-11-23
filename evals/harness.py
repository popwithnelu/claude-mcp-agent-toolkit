"""Small eval harness: run the agent over golden cases and score the answers."""
import json

from agent.claude_client import ClaudeAgent
from mcp_server.tools import TOOLS


def load_cases(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def score_case(expected_contains: list[str], answer: str) -> float:
    text = answer.lower()
    if not expected_contains:
        return 1.0
    hits = sum(1 for phrase in expected_contains if phrase.lower() in text)
    return hits / len(expected_contains)


def run_evals(cases: list[dict], agent: ClaudeAgent | None = None) -> dict:
    agent = agent or ClaudeAgent(TOOLS)
    per_case = {}
    for case in cases:
        result = agent.run(case["prompt"])
        per_case[case["id"]] = score_case(case["expected_contains"], result["answer"])
    mean = sum(per_case.values()) / max(len(per_case), 1)
    return {"mode": agent.mode, "mean": round(mean, 4), "per_case": per_case}

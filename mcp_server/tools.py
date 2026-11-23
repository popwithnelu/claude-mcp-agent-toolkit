"""Real tools exposed by the MCP server (also directly unit-testable)."""
import ast
import operator
import os

DOCS = {
    "rag-guide": "Retrieval augmented generation grounds a language model on retrieved documents. Chunking, embeddings and vector search are the core building blocks of a RAG pipeline.",
    "mcp-intro": "The Model Context Protocol (MCP) is an open standard for connecting AI applications to external tools and data sources through a common client-server protocol.",
    "prompt-caching": "Prompt caching lets you reuse stable prompt prefixes across Claude API calls, reducing latency and cost for repeated context such as long instructions or documents.",
}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def document_search(query: str) -> list[dict]:
    q = set(query.lower().split())
    hits = []
    for doc_id, text in DOCS.items():
        score = len(q & set(text.lower().split()))
        if score:
            hits.append({"doc_id": doc_id, "score": score, "text": text})
    return sorted(hits, key=lambda h: -h["score"])


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("unsupported expression")


def calculator(expression: str) -> float:
    """Safely evaluate an arithmetic expression (no names, no calls)."""
    return _eval_node(ast.parse(expression, mode="eval"))


def file_summarizer(path: str, max_chars: int = 200) -> dict:
    with open(path) as f:
        text = f.read()
    words = text.split()
    return {"path": os.path.basename(path), "word_count": len(words),
            "summary": text[:max_chars].strip()}


TOOLS = {
    "document_search": {
        "description": "Search the built-in document collection for a query.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        "handler": lambda a: document_search(a["query"]),
    },
    "calculator": {
        "description": "Evaluate an arithmetic expression safely.",
        "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        "handler": lambda a: calculator(a["expression"]),
    },
    "file_summarizer": {
        "description": "Summarize a local text file (word count + excerpt).",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        "handler": lambda a: file_summarizer(a["path"]),
    },
}

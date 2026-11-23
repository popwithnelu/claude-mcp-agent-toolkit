"""Claude API agent client demonstrating:

- tool use / function calling loop (messages + tool_result blocks)
- prompt caching (cache_control on the stable system prompt)
- structured outputs (request + validate a JSON answer against a schema)
- graceful mock/offline mode when ANTHROPIC_API_KEY is not set
"""
import json
import os

SYSTEM_PROMPT = (
    "You are a precise research assistant. Use the available tools when a "
    "question needs documents or arithmetic, and answer concisely."
)

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "used_tools": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "used_tools"],
}


def validate_structured(payload: dict, schema: dict = ANSWER_SCHEMA) -> bool:
    for key in schema.get("required", []):
        if key not in payload:
            return False
    return isinstance(payload.get("answer"), str) and isinstance(payload.get("used_tools"), list)


class MockClaude:
    """Offline stand-in: routes obvious intents to tools, then answers."""

    def __init__(self, tools: dict):
        self.tools = tools

    def run(self, user_message: str) -> dict:
        used = []
        notes = []
        msg = user_message.lower()
        if "calculate" in msg or "compute" in msg:
            expr = user_message.split(":", 1)[-1].strip() if ":" in user_message else "2 + 2"
            notes.append(f"calculator({expr}) = {self.tools['calculator']['handler']({'expression': expr})}")
            used.append("calculator")
        if "search" in msg or "document" in msg or "rag" in msg or "mcp" in msg:
            hits = self.tools["document_search"]["handler"]({"query": user_message})
            notes.append(f"document_search found {len(hits)} doc(s)")
            used.append("document_search")
        answer = "Mock answer. " + ("; ".join(notes) if notes else "No tools needed.")
        return {"answer": answer, "used_tools": used}


class ClaudeAgent:
    def __init__(self, tools: dict, model: str = "claude-sonnet-4-5"):
        self.tools = tools
        self.model = model
        self.mode = "mock"
        self._client = None
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic()
                self.mode = "claude"
            except Exception:
                self._client = None
        self._mock = MockClaude(tools)

    def _tool_specs(self) -> list[dict]:
        return [{"name": n, "description": t["description"], "input_schema": t["input_schema"]}
                for n, t in self.tools.items()]

    def run(self, user_message: str) -> dict:
        """Tool-use loop: keep calling Claude until it stops requesting tools,
        then return a structured (schema-validated) answer."""
        if self.mode == "mock":
            return self._mock.run(user_message)
        messages = [{"role": "user", "content": user_message}]
        used = []
        while True:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                # Prompt caching: the stable system prompt is marked cacheable.
                system=[{"type": "text", "text": SYSTEM_PROMPT,
                         "cache_control": {"type": "ephemeral"}}],
                tools=self._tool_specs(),
                messages=messages,
            )
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                text = "".join(b.text for b in resp.content if hasattr(b, "text"))
                payload = {"answer": text, "used_tools": used}
                if not validate_structured(payload):
                    raise ValueError("structured output failed schema validation")
                return payload
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for call in tool_uses:
                used.append(call.name)
                out = self.tools[call.name]["handler"](call.input)
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": json.dumps(out)})
            messages.append({"role": "user", "content": results})

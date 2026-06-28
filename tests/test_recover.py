"""Tool-call recovery fallback chain: extract a tool_use from text when a model
emits a tool call in a format the active dialect doesn't parse (Claude XML, bare
JSON with name/tool_id, Mistral array, Qwen XML).

Run:  uv run python tests/test_recover.py
"""

import sys

sys.path.insert(0, ".")

from server.prompting import recover_tool_call

SCH = {
    "read_file": {"path": "string"},
    "get_weather": {"city": "string"},
    "grep": {"pattern": "string", "max": "integer"},
}


def call(text):
    r = recover_tool_call(text, SCH)
    return None if r is None else (r["name"], r["input"])


# Claude-style <function_calls><invoke> XML (what Qwen3.6 emits)
claude = (
    "<function_calls>\n<invoke>\n<tool_name>read_file</tool_name>\n"
    "<arguments>\n<path>src/main.py</path>\n</arguments>\n</invoke>\n</function_calls>"
)
assert call(claude) == ("read_file", {"path": "src/main.py"}), call(claude)

# <invoke name="..."> attribute form
inv = (
    '<function_calls><invoke name="get_weather"><arguments><city>Paris</city></arguments></invoke>'
)
assert call(inv) == ("get_weather", {"city": "Paris"}), call(inv)

# bare JSON with tool_id / arguments (the other Qwen3.6 form)
js1 = 'Sure.\n{\n  "tool_id": "get_weather",\n  "arguments": { "city": "Paris" }\n}'
assert call(js1) == ("get_weather", {"city": "Paris"}), call(js1)

# standard JSON name + arguments, with type coercion (max -> int)
js2 = '{"name": "grep", "arguments": {"pattern": "TODO", "max": 5}}'
assert call(js2) == ("grep", {"pattern": "TODO", "max": 5}), call(js2)

# JSON "parameters" alias
js3 = '{"name": "read_file", "parameters": {"path": "a.py"}}'
assert call(js3) == ("read_file", {"path": "a.py"}), call(js3)

# Mistral array
mis = '[TOOL_CALLS][{"name": "get_weather", "arguments": {"city": "Berlin"}}]'
assert call(mis) == ("get_weather", {"city": "Berlin"}), call(mis)

# Qwen native XML still recovers (+ coerce)
qwen = (
    "<tool_call>\n<function=grep>\n<parameter=pattern>\nTODO\n</parameter>\n"
    "<parameter=max>\n3\n</parameter>\n</function>\n</tool_call>"
)
assert call(qwen) == ("grep", {"pattern": "TODO", "max": 3}), call(qwen)

# plain prose -> nothing (no false positives)
assert call("Here is the weather: it's sunny in Paris today, around 18C.") is None
assert call("") is None
assert call("a JSON-less {not real json} blob") is None
print("recover_tool_call: OK")
print("all recover tests passed")

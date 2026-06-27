"""Best-effort tool-call RECOVERY — a fallback chain for when the served model
emits a tool call in a format the active dialect doesn't parse.

Distilled models are unreliable here: e.g. Qwen3.6, told to use Qwen's
<tool_call><function=name> form, instead emits Claude's <function_calls><invoke>
XML or a bare JSON {"name":…,"arguments":…} — so the dialect parser misses it and
it leaks as text. When the turn ends with NO parsed tool call, the pipeline runs
this over the assembled text and tries each known format in turn. Returns a
{id, name, input} tool_use, or None if nothing tool-shaped is found.
"""

import json
import re
from typing import Any

from .wire import Schemas, new_tool_use_id


def recover_tool_call(text: str, schemas: Schemas | None = None) -> dict | None:
    """Try each known tool-call format on `text`; return a tool_use or None."""
    if not text or ("<" not in text and "{" not in text and "[TOOL_CALLS]" not in text):
        return None
    for parse in (_qwen_xml, _claude_xml, _mistral_array, _json_object):
        got = parse(text)
        if got and got[0]:
            name, args = got
            args = {k: _coerce(v, (schemas or {}).get(name, {}).get(k)) for k, v in args.items()}
            return {"id": new_tool_use_id(), "name": name, "input": args}
    return None


def _qwen_xml(text: str):
    """<tool_call><function=NAME><parameter=k>v</parameter>…"""
    m = re.search(r"<function=([^>\n]+)>", text)
    if not m:
        return None
    args = {
        pm.group(1).strip(): pm.group(2)
        for pm in re.finditer(r"<parameter=([^>\n]+)>\n?(.*?)\n?</parameter>", text, re.S)
    }
    return m.group(1).strip(), args


def _claude_xml(text: str):
    """<function_calls><invoke><tool_name>NAME</tool_name><arguments><k>v</k>…"""
    m = re.search(r"<tool_name>\s*(.*?)\s*</tool_name>", text, re.S) or re.search(
        r"<invoke\s+name=[\"']([^\"']+)[\"']", text
    )
    if not m:
        return None
    am = re.search(r"<arguments>(.*?)</arguments>", text, re.S)
    body = am.group(1) if am else text
    args = {
        pm.group(1): pm.group(2).strip()
        for pm in re.finditer(r"<([a-zA-Z_][\w.\-]*)>\n?(.*?)\n?</\1>", body, re.S)
        if pm.group(1) not in ("arguments", "invoke", "tool_name", "function_calls")
    }
    return m.group(1).strip(), args


def _mistral_array(text: str):
    """[TOOL_CALLS][{"name":…,"arguments":…}]"""
    m = re.search(r"\[TOOL_CALLS\]\s*(\[.*\])", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        c = data[0]
        return c.get("name"), c.get("arguments") or c.get("parameters") or {}
    return None


def _json_object(text: str):
    """A bare JSON tool call: {"name"|"tool_name"|"tool_id": …, "arguments"|"parameters": {…}}."""
    for obj in _json_objects(text):
        name = obj.get("name") or obj.get("tool_name") or obj.get("tool_id") or obj.get("function")
        args = obj.get("arguments")
        if args is None:
            args = obj.get("parameters")
        if args is None:
            args = obj.get("input", {})
        if name and isinstance(args, dict):
            return name, args
    return None


def _json_objects(text: str):
    """Yield each top-level {...} parsed as JSON (brace-matched, string-aware)."""
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, in_str, esc = 0, False, False
        for j in range(i, n):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        yield json.loads(text[i : j + 1])
                    except json.JSONDecodeError:
                        pass
                    i = j + 1
                    break
        else:
            return


def _coerce(value: Any, schema_type: str | None) -> Any:
    if not isinstance(value, str):
        return value
    try:
        if schema_type == "integer":
            return int(value.strip())
        if schema_type == "number":
            return float(value.strip())
        if schema_type == "boolean":
            return value.strip().lower() in ("true", "1", "yes")
        if schema_type in ("array", "object"):
            return json.loads(value)
    except (ValueError, json.JSONDecodeError):
        pass
    return value

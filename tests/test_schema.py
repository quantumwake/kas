"""Validation tests for the request schema: the max_tokens output cap (a
localhost DoS guard) and that an unmodified default request still validates.
No model or server needed.

Run:  uv run python tests/test_schema.py
"""

import sys

sys.path.insert(0, ".")

from pydantic import ValidationError

from server.schema import MAX_OUTPUT_TOKENS, MessagesRequest

_base = {"model": "m", "messages": [{"role": "user", "content": "hi"}]}

# a default request validates, and keeps the historical default
assert MessagesRequest(**_base).max_tokens == 1024

# exactly at the cap is allowed
assert MessagesRequest(**_base, max_tokens=MAX_OUTPUT_TOKENS).max_tokens == MAX_OUTPUT_TOKENS

# over the cap is rejected (-> RequestValidationError -> Anthropic error envelope)
try:
    MessagesRequest(**_base, max_tokens=MAX_OUTPUT_TOKENS + 1)
    raise AssertionError("max_tokens over the cap should fail validation")
except ValidationError:
    pass

# zero / negative rejected (ge=1)
for bad in (0, -1):
    try:
        MessagesRequest(**_base, max_tokens=bad)
        raise AssertionError(f"max_tokens={bad} should fail validation")
    except ValidationError:
        pass

print("schema validation tests passed")

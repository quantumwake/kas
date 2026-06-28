"""Image→text plumbing that doesn't need mlx-vlm or a VLM: the ImageBlock
schema, translate preserving images into multimodal user content, the VLM
backend's image extraction, and backend registration/gating.

Run:  uv run python tests/test_vision.py
"""

import base64
import sys

sys.path.insert(0, ".")

from server import backends
from server.backends.mlx_vlm import _prompt_text, _resolve_images
from server.prompting import to_chat_messages
from server.schema import ImageBlock, Message

# 1. ImageBlock parses in a Message (Anthropic content-block union).
m = Message(
    role="user",
    content=[
        {"type": "text", "text": "what is this?"},
        {"type": "image", "source": {"type": "path", "path": "/tmp/a.png"}},
    ],
)
assert any(isinstance(b, ImageBlock) for b in m.content)
print("ImageBlock schema: OK")

# 2. translate preserves images as a multimodal user content list (text + image).
chat = to_chat_messages([m], system=None, tool_choice=None)
user = [c for c in chat if c["role"] == "user"][0]
assert isinstance(user["content"], list), user
kinds = [e["type"] for e in user["content"]]
assert kinds == ["text", "image"], kinds
assert user["content"][1]["source"]["path"] == "/tmp/a.png"
print("translate multimodal content: OK")

# 2b. a text-only user message stays a plain string (no regression for text models).
plain = to_chat_messages([Message(role="user", content="hello")], None, None)
assert plain[-1]["content"] == "hello", plain
print("translate text unchanged: OK")

# 3. _resolve_images: path passes through; base64 is written to a temp file.
png_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
msgs = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "x"},
            {"type": "image", "source": {"type": "path", "path": "/tmp/keep.png"}},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": png_b64},
            },
        ],
    },
]
paths = _resolve_images(msgs)
assert paths[0] == "/tmp/keep.png"
assert paths[1].endswith(".png") and open(paths[1], "rb").read() == b"\x89PNG\r\n\x1a\nfake"
assert _prompt_text(msgs[0]["content"]) == "x"
print("_resolve_images: OK")

# 4. backend registry: mlx_vlm registered + Apple-Silicon gated; not in
#    available_backends unless installed; detection never routes to it when absent.
assert "mlx_vlm" in backends.BACKENDS
b = backends.BACKENDS["mlx_vlm"]
assert b.installed() == backends._has("mlx_vlm")()
if not b.installed():
    assert "mlx_vlm" not in backends.available_backends()
    # a vision id must NOT route to mlx_vlm when the package is missing
    assert backends._detect_backend("mlx-community/Qwen2.5-VL-7B-Instruct-4bit") != "mlx_vlm"
print("backend registration + gating: OK")


# 5. TUI: file-drop capture pulls image paths out of the line and stages them;
#    user_content emits PATH-source blocks (no base64 by default).
import tempfile  # noqa: E402
import types  # noqa: E402

from agent.tui.app import AgentApp  # noqa: E402
from agent.tui.commands import CommandHandler  # noqa: E402

img = tempfile.mktemp(suffix=".png")
open(img, "wb").close()


class DropApp(CommandHandler):
    def __init__(self):
        self._pending_images = []
        self.writes = []

    def body_write(self, r):
        self.writes.append(str(r))


app = DropApp()
# a shell-escaped dropped path (spaces escaped, as iTerm2 pastes) + prose
rest = app._capture_dropped_images(f"look at this {img}")
assert app._pending_images == [img], app._pending_images
assert rest.strip() == "look at this", repr(rest)
# non-image prose is untouched, nothing staged
app2 = DropApp()
assert app2._capture_dropped_images("just text here") == "just text here"
assert app2._pending_images == []
print("file-drop capture: OK")

# user_content: PATH source by default (no base64), cleared after build.
uc = types.SimpleNamespace(_pending_images=[img])
content = AgentApp.user_content(uc, "what is this?")
assert isinstance(content, list)
assert content[0] == {"type": "text", "text": "what is this?"}
assert content[1]["type"] == "image" and content[1]["source"]["type"] == "path"
assert content[1]["source"]["path"].endswith(".png")
assert uc._pending_images == []  # stage cleared
# no images -> plain string passthrough
uc2 = types.SimpleNamespace(_pending_images=[])
assert AgentApp.user_content(uc2, "hi") == "hi"
print("user_content path-source: OK")

print("all vision tests passed")

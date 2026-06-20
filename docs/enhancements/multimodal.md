# Enhancement: multimodal — image/embeddings serving, analysis, voice

Status: **parked / vision.** "For now, do the simple thing" — typed
endpoints/tools per modality, not everything forced through the text token API.

## 1. Hosting non-text models in the serve API

The Messages API is a **text-token** protocol; diffusion (image bytes) and
embedders (vectors) don't fit its response shape. So don't jam them into
`/v1/messages` — give each model class its **own typed endpoint + adapter**, the
way OpenAI/Anthropic split `/images`, `/embeddings`, `/messages`:

- `/v1/images`  — text → image; returns a file path (or base64). Adapter today =
  the `generate_image` tool shelling out to **mflux** (simple, already here).
- `/v1/embeddings` — text → vector; small MLX/HF embedder. Unlocks the **hybrid
  vector RAG** the recall code already left a seam for.

The "adapter" per endpoint just knows how to invoke that model class and
serialize its output (path for images, array for vectors). Use existing
mlx/HF/transformers adapters; roll our own only if needed. On 128GB a small
embedder/diffuser co-resides with the LLM fine.

## 2. Analyzing images + audio (multimodal INPUT)

- **Audio = simple now.** Whisper transcription (mlx-whisper; whisper-large
  models are already downloaded). A `transcribe` tool/endpoint → text the agent
  reasons over. Do this first.
- **Images = bigger.** Needs (a) a vision model (mlx-vlm: Qwen-VL / Gemma) and
  (b) the schema to carry image content blocks (text-only today). Then the agent
  can "look at" screenshots/sprites — closes the loop for the art workflow.

## 3. Voice interface

A push-to-talk loop, minimal deps:
- **STT**: mic → **Whisper** (mlx) → text → feed as the prompt.
- **TTS**: agent reply → speech. Dead-simple first cut = macOS **`say`**; later a
  proper TTS model.
- Mic capture needs an audio lib (sounddevice/pyaudio), opt-in.
- A `/voice` mode in the TUI toggles it.

## Convergence
All of this makes the server a **multi-modal model host** (LLM + diffusion +
embedder + VLM + Whisper), each behind a typed endpoint or tool — and each is
just another **skill** under the dispatcher ([tools.md](tools.md) /
[skills.md](skills.md)). Sequence: Whisper transcribe → embeddings+hybrid RAG →
voice loop → VLM image input.

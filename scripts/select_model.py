"""Interactive picker over locally downloaded HF models.

Prints the chosen model id to stdout (everything else goes to stderr) so it
composes with `make start MODEL=$(...)`.
"""

import pathlib
import sys

HUB = pathlib.Path.home() / ".cache" / "huggingface" / "hub"


def downloaded_models() -> list[str]:
    models = []
    for d in sorted(HUB.glob("models--*")):
        if not list(d.glob("snapshots/*/config.json")):
            continue  # not a loadable model (tokenizer-only or partial)
        models.append(d.name.removeprefix("models--").replace("--", "/"))
    return models


def main() -> None:
    models = downloaded_models()
    if not models:
        print("no downloaded models found — run: make download MODEL=<id>", file=sys.stderr)
        sys.exit(1)
    print("downloaded models:", file=sys.stderr)
    for i, m in enumerate(models, 1):
        print(f"  {i}) {m}", file=sys.stderr)
    try:
        raw = input("model #: ")
        choice = int(raw)
        if not 1 <= choice <= len(models):
            raise ValueError
    except (ValueError, EOFError):
        print("invalid selection", file=sys.stderr)
        sys.exit(1)
    print(models[choice - 1])


if __name__ == "__main__":
    main()

"""/viz — visualize what the model is doing per token (confidence / alternatives /
entropy). Each overlay toggles independently; turning any on makes the agent ask
the server for logprobs (so the cost is only paid while viz is on)."""

from rich.text import Text

from .base import Command


class VizCommand(Command):
    name = "/viz"
    summary = "visualize per-token confidence / alternatives / entropy"
    usage = "[heatmap|topk|entropy|all|off]"
    subcommands = (
        ("heatmap", "colour streamed tokens by confidence (green sure → red coin-flip)"),
        ("topk", "show the candidate tokens the model weighed each step"),
        ("entropy", "drive the fx bar from per-token uncertainty"),
        ("all", "turn all three on"),
        ("off", "turn viz off"),
    )

    def run(self, app, arg: str) -> None:
        m = app.viz
        toks = arg.strip().lower().split()
        valid = ("heatmap", "topk", "entropy")
        if toks in ([], ["status"]):
            pass  # just report the current state
        elif toks in (["all"], ["on"]):
            m.heatmap = m.topk = m.entropy = True
        elif toks[0] in ("off", "none"):
            m.heatmap = m.topk = m.entropy = False
        elif all(t in valid for t in toks):
            # set EXACTLY the named overlays (not a toggle): '/viz heatmap' -> just
            # heatmap; '/viz heatmap entropy' -> those two; the rest off.
            m.heatmap, m.topk, m.entropy = (v in toks for v in valid)
        else:
            app.body_write(Text("usage: /viz [heatmap|topk|entropy …|all|off]", style="yellow"))
            return
        if not (m.topk or m.entropy):  # the panel only serves top-k / entropy
            getattr(app, "hide_viz_panel", lambda: None)()
        app.body_write(Text(m.summary(), style="#c792ea"))
        if m.any_on:
            app.body_write(Text("  (server emits per-token logprobs only while viz is on)", "dim"))

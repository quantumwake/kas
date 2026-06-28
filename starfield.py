"""
3D Starfield - A Python application that projects and animates stars moving through space.
Uses matplotlib for 3D projection and animation.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import random

# ─── Configuration ───────────────────────────────────────────────
NUM_STARS = 500
STAR_FIELD_DEPTH = 2000          # max Z distance
STAR_SPEED = 3                   # pixels per frame (screen-space)
FOCAL_LENGTH = 500               # perspective projection focal length
BG_COLOR = "#000011"             # deep space blue-black
STAR_COLORS = ["white", "lightblue", "lightyellow", "lightpink"]

# ─── Star class ──────────────────────────────────────────────────
class Star:
    """Represents a single star with 3D position and visual properties."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Place star at a random position behind the viewer."""
        self.x = random.uniform(-500, 500)
        self.y = random.uniform(-500, 500)
        self.z = random.uniform(10, STAR_FIELD_DEPTH)
        self.size = random.uniform(0.5, 2.5)
        self.color = random.choice(STAR_COLORS)
        self.speed = random.uniform(1.5, 4.0)

    def move(self, dt):
        """Move star toward the viewer along Z."""
        self.z -= self.speed * dt
        if self.z <= 1:
            self.reset()

    def project(self):
        """Perspective-project 3D position onto 2D screen coordinates."""
        if self.z < 1:
            return None, None
        scale = FOCAL_LENGTH / self.z
        screen_x = self.x * scale
        screen_y = self.y * scale
        return screen_x, screen_y


# ─── Build star field ────────────────────────────────────────────
stars = [Star() for _ in range(NUM_STARS)]

# ─── Matplotlib figure ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 8))
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)
ax.set_xlim(-500, 500)
ax.set_ylim(-500, 500)
ax.set_aspect("equal")
ax.axis("off")
fig.suptitle("3D Starfield Projection", color="white", fontsize=14, y=0.98)

# Scatter collection (all stars as one artist for performance)
scatter = ax.scatter([], [], s=[], c=[], edgecolors="none", zorder=2)

# ─── Animation helpers ───────────────────────────────────────────
def _init():
    scatter.set_offsets(np.empty((0, 2)))
    scatter.set_sizes(np.array([]))
    scatter.set_facecolors([])
    return scatter,


def _update(frame):
    """Move every star, re-project, and update the scatter plot."""
    positions = []
    sizes = []
    colors = []

    for star in stars:
        star.move(1)
        sx, sy = star.project()
        if sx is None:
            continue

        # Brightness increases as star gets closer
        brightness = min(1.0, 500.0 / star.z)
        positions.append([sx, sy])
        sizes.append(star.size * (300.0 / star.z))
        # Fade color toward white as brightness increases
        colors.append((brightness, brightness, brightness))

    if positions:
        arr = np.array(positions)
        scatter.set_offsets(arr)
        scatter.set_sizes(np.array(sizes) * 10)
        scatter.set_facecolors(colors)

    return scatter,


# ─── Create & launch animation ──────────────────────────────────
anim = FuncAnimation(
    fig,
    _update,
    init_func=_init,
    frames=None,
    interval=20,          # ms between frames  (~50 fps)
    blit=False,           # True can clip in 3D; False is safer
    cache_frame_data=False,
)

print("Press Ctrl+C to stop the animation.")
plt.show()

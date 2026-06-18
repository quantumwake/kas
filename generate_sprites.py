import sys
sys.path.insert(0, '.')
from agent.adapters.tools.image import generate_image
from agent import config

# Override the art binary to use the venv one
config.ART_BIN = '.venv/bin/mflux-generate-flux2'

vehicles = [
    (0, 'Steam Locomotive', '#8b4513', 'train'),
    (1, 'Diesel Locomotive', '#228b22', 'train'),
    (2, 'Electric Locomotive', '#4169e1', 'train'),
    (3, 'High Speed Train', '#dc143c', 'train'),
    (4, 'Passenger Car', '#228b22', 'train'),
    (5, 'Cargo Wagon', '#8b4513', 'train'),
    (6, 'Minibus', '#ff6347', 'bus'),
    (7, 'Bus', '#228b22', 'bus'),
    (8, 'Coach', '#4169e1', 'bus'),
    (9, 'Cargo Truck', '#8b4513', 'truck'),
    (10, 'Long Distance Truck', '#b8860b', 'truck'),
    (11, 'Mail Van', '#ffff00', 'van'),
    (12, 'Cessna', '#ffffff', 'plane'),
    (13, 'DC-3', '#c0c0c0', 'plane'),
    (14, 'Boeing 707', '#4169e1', 'plane'),
    (15, 'Cargo Plane', '#8b4513', 'plane'),
    (16, 'Air Mail Plane', '#ffff00', 'plane'),
    (17, 'Cargo Ship', '#8b4513', 'ship'),
    (18, 'Passenger Ship', '#228b22', 'ship'),
    (19, 'Ferry', '#4169e1', 'ship'),
]

workdir = 'ttm-game'
out_dir = 'ttm-game/public/assets/vehicles'

for vid, name, color, vtype in vehicles:
    path = f'{out_dir}/v{vid}.png'
    prompt = (
        f"Strict 3/4 isometric view of a {name}, "
        f"primary color {color}, "
        f"Transport Tycoon game sprite style, "
        f"clean vector art, white background, centered, no text, no shadows"
    )
    print(f"Generating {name}...")
    result, error = generate_image(prompt, workdir, path=path, seed=vid * 1234, steps=4)
    if error:
        print(f"  ERROR: {result}")
    else:
        print(f"  OK: {result}")

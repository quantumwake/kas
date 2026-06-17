// ===== CANVAS RENDERER =====

import { useRef, useEffect, useCallback, useMemo } from 'react';
import {
  MAP_SIZE, TILE_SIZE, TERRAIN, TERRAIN_COLORS, TILE, SURFACE_COLORS,
  VEHICLE_DEFS, INDUSTRY_TYPES, VEHICLE_CLASSES
} from '../game/constants.js';

// Pre-rendered tile cache
const tileCache = new Map();

function getTileCanvas(terrainType, surfaceType, featureType) {
  const key = `${terrainType}_${surfaceType}_${featureType}`;
  if (tileCache.has(key)) return tileCache.get(key);

  const size = TILE_SIZE * 4; // base render size
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  // Base terrain
  let baseColor = TERRAIN_COLORS[terrainType] || '#4a8c3f';
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, size, size);

  // Terrain detail
  if (terrainType === TERRAIN.WATER) {
    ctx.fillStyle = 'rgba(100,180,255,0.15)';
    ctx.fillRect(0, size * 0.3, size, 2);
    ctx.fillRect(0, size * 0.7, size, 2);
  } else if (terrainType === TERRAIN.GRASS) {
    ctx.fillStyle = 'rgba(0,80,0,0.2)';
    for (let i = 0; i < 4; i++) {
      ctx.fillRect(Math.random() * size, Math.random() * size, 2, 3);
    }
  } else if (terrainType === TERRAIN.DESERT) {
    ctx.fillStyle = 'rgba(200,180,100,0.3)';
    for (let i = 0; i < 6; i++) {
      ctx.fillRect(Math.random() * size, Math.random() * size, 3, 2);
    }
  } else if (terrainType === TERRAIN.MOUNTAIN) {
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.moveTo(size * 0.2, size);
    ctx.lineTo(size * 0.5, size * 0.2);
    ctx.lineTo(size * 0.8, size);
    ctx.fill();
  }

  // Surface overlay
  if (surfaceType === TILE.ROAD) {
    ctx.fillStyle = '#444444';
    ctx.fillRect(0, size / 2 - size * 0.15, size, size * 0.3);
    ctx.fillRect(size / 2 - size * 0.15, 0, size * 0.3, size);
    // Road line
    ctx.fillStyle = '#cccc44';
    ctx.fillRect(size / 2 - 1, 0, 2, size * 0.4);
    ctx.fillRect(size / 2 - 1, size * 0.6, 2, size * 0.4);
  } else if (surfaceType === TILE.RAIL) {
    ctx.fillStyle = '#3a2a1a';
    ctx.fillRect(size * 0.3, 0, size * 0.4, size);
    // Rails
    ctx.fillStyle = '#aaa';
    ctx.fillRect(size * 0.35, 0, 2, size);
    ctx.fillRect(size * 0.6, 0, 2, size);
    // Sleepers
    ctx.fillStyle = '#6b4226';
    for (let y = 0; y < size; y += 6) {
      ctx.fillRect(size * 0.32, y, size * 0.36, 3);
    }
  } else if (surfaceType === TILE.STATION) {
    ctx.fillStyle = '#1565C0';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#1976D2';
    ctx.fillRect(2, 2, size - 4, size - 4);
    // Platform
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, size * 0.1, size, 3);
    ctx.fillRect(0, size * 0.85, size, 3);
  } else if (surfaceType === TILE.BUS_STOP) {
    ctx.fillStyle = '#E65100';
    ctx.fillRect(size / 2 - 3, 0, 6, size);
    ctx.fillStyle = '#fff';
    ctx.fillRect(size / 2 - 2, size * 0.3, 4, size * 0.4);
  } else if (surfaceType === TILE.TRUCK_STOP) {
    ctx.fillStyle = '#8B6914';
    ctx.fillRect(size / 2 - 4, 0, 8, size);
  } else if (surfaceType === TILE.AIRPORT) {
    ctx.fillStyle = '#555';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, size / 2 - 2, size, 4);
    ctx.fillRect(size / 2 - 2, 0, 4, size);
  } else if (surfaceType === TILE.DOCK) {
    ctx.fillStyle = '#5D3A1A';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#8B6914';
    ctx.fillRect(0, 0, size, size * 0.3);
    // Bollards
    ctx.fillStyle = '#333';
    ctx.fillRect(size * 0.2, size * 0.1, 4, 4);
    ctx.fillRect(size * 0.7, size * 0.1, 4, 4);
  } else if (surfaceType === TILE.BRIDGE) {
    ctx.fillStyle = '#777';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#999';
    ctx.fillRect(size * 0.2, 0, size * 0.6, size);
  } else if (surfaceType === TILE.SIGNAL) {
    ctx.fillStyle = '#cc0000';
    ctx.fillRect(size / 2 - 3, size * 0.2, 6, size * 0.6);
    ctx.fillStyle = '#ffff00';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // Features
  if (featureType === 1) { // Tree
    ctx.fillStyle = '#2d5a1e';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 4, size * 0.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#1a3a10';
    ctx.beginPath();
    ctx.arc(size / 2 - 3, size / 2 - 6, size * 0.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#4a2a0a';
    ctx.fillRect(size / 2 - 2, size / 2, 4, size * 0.3);
  } else if (featureType === 2) { // House
    ctx.fillStyle = '#d4a574';
    ctx.fillRect(size * 0.25, size * 0.3, size * 0.5, size * 0.5);
    // Roof
    ctx.fillStyle = '#8B4513';
    ctx.beginPath();
    ctx.moveTo(size * 0.2, size * 0.3);
    ctx.lineTo(size * 0.5, size * 0.1);
    ctx.lineTo(size * 0.8, size * 0.3);
    ctx.fill();
    // Window
    ctx.fillStyle = '#ffff88';
    ctx.fillRect(size * 0.4, size * 0.4, size * 0.2, size * 0.2);
  } else if (featureType === 3) { // Industry
    ctx.fillStyle = '#555';
    ctx.fillRect(size * 0.15, size * 0.25, size * 0.7, size * 0.55);
    // Chimney
    ctx.fillStyle = '#333';
    ctx.fillRect(size * 0.6, size * 0.1, size * 0.15, size * 0.3);
    // Door
    ctx.fillStyle = '#222';
    ctx.fillRect(size * 0.4, size * 0.55, size * 0.2, size * 0.25);
  }

  tileCache.set(key, canvas);
  return canvas;
}

// ---- React Component ----

export default function GameCanvas({ state, onTileClick, onTileHover }) {
  const canvasRef = useRef(null);
  const minimapRef = useRef(null);
  const animFrameRef = useRef(null);

  // Calculate visible tile range
  const getVisibleRange = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const ts = state.zoom;
    const w = canvas.width / ts;
    const h = canvas.height / ts;
    const cx = state.cameraX;
    const cy = state.cameraY;
    return {
      x1: Math.max(0, Math.floor(cx - w / 2)),
      y1: Math.max(0, Math.floor(cy - h / 2)),
      x2: Math.min(MAP_SIZE - 1, Math.ceil(cx + w / 2)),
      y2: Math.min(MAP_SIZE - 1, Math.ceil(cy + h / 2)),
    };
  }, [state.cameraX, state.cameraY, state.zoom]);

  // Draw main canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const ts = state.zoom;

    // Resize canvas to fit window
    if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    }

    ctx.fillStyle = '#0a1520';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const range = getVisibleRange();
    if (!range) return;

    const offsetX = (canvas.width / 2) - state.cameraX * ts;
    const offsetY = (canvas.height / 2) - state.cameraY * ts;

    // Draw tiles
    for (let y = range.y1; y <= range.y2; y++) {
      for (let x = range.x1; x <= range.x2; x++) {
        const i = y * MAP_SIZE + x;
        const terrain = state.terrain[i];
        const surface = state.surface[i];
        const feature = state.features[i];

        const px = Math.floor(x * ts + offsetX);
        const py = Math.floor(y * ts + offsetY);

        // Get cached tile
        const tileCanvas = getTileCanvas(terrain, surface, feature);
        ctx.drawImage(tileCanvas, px, py, ts, ts);
      }
    }

    // Draw vehicles
    for (const vehicle of state.vehicles) {
      const def = VEHICLE_DEFS[vehicle.defId];
      if (!def) continue;
      drawVehicle(ctx, vehicle, ts, offsetX, offsetY, state.selectedVehicle === vehicle.id);
    }

    // Draw hover highlight
    if (state.hoveredTile) {
      const hx = Math.floor(state.hoveredTile.x * ts + offsetX);
      const hy = Math.floor(state.hoveredTile.y * ts + offsetY);
      ctx.strokeStyle = '#ffff00';
      ctx.lineWidth = 2;
      ctx.strokeRect(hx, hy, ts, ts);
    }

    // Draw build preview
    if (state.selectedTool && state.hoveredTile && state.selectedTool > 1) {
      drawBuildPreview(ctx, state, ts, offsetX, offsetY);
    }

    // Draw grid (subtle)
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (let x = range.x1; x <= range.x2; x++) {
      const px = Math.floor(x * ts + offsetX);
      ctx.beginPath();
      ctx.moveTo(px, 0);
      ctx.lineTo(px, canvas.height);
      ctx.stroke();
    }
    for (let y = range.y1; y <= range.y2; y++) {
      const py = Math.floor(y * ts + offsetY);
      ctx.beginPath();
      ctx.moveTo(0, py);
      ctx.lineTo(canvas.width, py);
      ctx.stroke();
    }

    // Draw minimap
    drawMinimap(state);
  }, [state, getVisibleRange, drawMinmap]);

  // Draw a single vehicle
  function drawVehicle(ctx, vehicle, ts, offsetX, offsetY, selected) {
    const def = VEHICLE_DEFS[vehicle.defId];
    if (!def) return;

    const px = vehicle.x * ts + offsetX;
    const py = vehicle.y * ts + offsetY;

    ctx.save();
    ctx.translate(px + ts / 2, py + ts / 2);

    if (def.cls === VEHICLE_CLASSES.TRAIN) {
      ctx.fillStyle = def.color;
      ctx.fillRect(-ts * 0.4, -ts * 0.15, ts * 0.8, ts * 0.3);
      ctx.fillStyle = '#333';
      ctx.fillRect(-ts * 0.1, -ts * 0.2, ts * 0.2, ts * 0.4);
      // Wheels
      ctx.fillStyle = '#222';
      ctx.beginPath();
      ctx.arc(-ts * 0.25, ts * 0.15, ts * 0.08, 0, Math.PI * 2);
      ctx.arc(ts * 0.25, ts * 0.15, ts * 0.08, 0, Math.PI * 2);
      ctx.fill();
    } else if (def.cls === VEHICLE_CLASSES.ROAD) {
      ctx.fillStyle = def.color;
      ctx.fillRect(-ts * 0.25, -ts * 0.2, ts * 0.5, ts * 0.4);
      ctx.fillStyle = '#333';
      ctx.fillRect(-ts * 0.25, -ts * 0.2, ts * 0.5, ts * 0.08);
      ctx.fillStyle = '#111';
      ctx.beginPath();
      ctx.arc(-ts * 0.15, ts * 0.2, ts * 0.06, 0, Math.PI * 2);
      ctx.arc(ts * 0.15, ts * 0.2, ts * 0.06, 0, Math.PI * 2);
      ctx.fill();
    } else if (def.cls === VEHICLE_CLASSES.AIR) {
      ctx.fillStyle = def.color;
      ctx.beginPath();
      ctx.moveTo(0, -ts * 0.4);
      ctx.lineTo(ts * 0.3, 0);
      ctx.lineTo(0, ts * 0.4);
      ctx.lineTo(-ts * 0.3, 0);
      ctx.fill();
      ctx.fillStyle = '#aaa';
      ctx.fillRect(-ts * 0.3, -ts * 0.05, ts * 0.6, ts * 0.1);
    } else if (def.cls === VEHICLE_CLASSES.WATER) {
      ctx.fillStyle = def.color;
      ctx.beginPath();
      ctx.moveTo(-ts * 0.35, 0);
      ctx.lineTo(0, -ts * 0.3);
      ctx.lineTo(ts * 0.35, 0);
      ctx.lineTo(0, ts * 0.3);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillRect(-ts * 0.08, -ts * 0.08, ts * 0.16, ts * 0.16);
    }

    // Cargo indicator
    if (vehicle.cargo.length > 0) {
      const total = vehicle.cargo.reduce((s, c) => s + c.amount, 0);
      if (total > 0) {
        ctx.fillStyle = '#0f0';
        ctx.fillRect(ts * 0.2, -ts * 0.35, ts * 0.1, ts * 0.1);
      }
    }

    // Broken down indicator
    if (vehicle.brokenDown) {
      ctx.fillStyle = '#ff0000';
      ctx.font = `${ts * 0.5}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText('⚠', 0, -ts * 0.3);
    }

    // Selection highlight
    if (selected) {
      ctx.strokeStyle = '#ffff00';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(0, 0, ts * 0.6, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.restore();
  }

  // Draw build preview
  function drawBuildPreview(ctx, state, ts, offsetX, offsetY) {
    if (!state.hoveredTile) return;
    const { x, y } = state.hoveredTile;
    const px = x * ts + offsetX;
    const py = y * ts + offsetY;

    ctx.fillStyle = 'rgba(0, 255, 0, 0.3)';
    ctx.fillRect(px, py, ts, ts);
  }

  // Draw minimap
  function drawMinimap() {
    const minimap = minimapRef.current;
    if (!minimap) return;
    const ctx = minimap.getContext('2d');
    const w = minimap.width;
    const h = minimap.height;

    ctx.fillStyle = '#0a1520';
    ctx.fillRect(0, 0, w, h);

    const scale = w / MAP_SIZE;
    const step = 4;

    // Draw terrain
    for (let y = 0; y < MAP_SIZE; y += step) {
      for (let x = 0; x < MAP_SIZE; x += step) {
        const i = y * MAP_SIZE + x;
        ctx.fillStyle = TERRAIN_COLORS[state.terrain[i]] || '#4a8c3f';
        ctx.fillRect(x * scale, y * scale, scale * step + 1, scale * step + 1);

        if (state.surface[i] === TILE.ROAD) {
          ctx.fillStyle = '#888';
          ctx.fillRect(x * scale, y * scale, scale * step, scale * step);
        } else if (state.surface[i] === TILE.RAIL) {
          ctx.fillStyle = '#aaa';
          ctx.fillRect(x * scale, y * scale, scale * step, scale * step);
        } else if (state.surface[i] === TILE.STATION) {
          ctx.fillStyle = '#2196F3';
          ctx.fillRect(x * scale, y * scale, scale * step, scale * step);
        } else if (state.surface[i] === TILE.AIRPORT) {
          ctx.fillStyle = '#fff';
          ctx.fillRect(x * scale, y * scale, scale * step, scale * step);
        }
      }
    }

    // Towns
    for (const town of state.towns) {
      ctx.fillStyle = '#00ff00';
      ctx.fillRect(town.x * scale - 2, town.y * scale - 2, 5, 5);
    }

    // Industries
    for (const ind of state.industries) {
      ctx.fillStyle = '#ff4444';
      ctx.fillRect(ind.x * scale - 2, ind.y * scale - 2, 4, 4);
    }

    // Vehicles
    for (const v of state.vehicles) {
      const def = VEHICLE_DEFS[v.defId];
      ctx.fillStyle = def?.color || '#fff';
      ctx.fillRect(v.x * scale - 1, v.y * scale - 1, 3, 3);
    }

    // Camera viewport
    const range = getVisibleRange();
    if (range) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        range.x1 * scale, range.y1 * scale,
        (range.x2 - range.x1) * scale, (range.y2 - range.y1) * scale
      );
    }
  }

  // Render loop
  useEffect(() => {
    let running = true;
    const loop = () => {
      if (!running) return;
      draw();
      animFrameRef.current = requestAnimationFrame(loop);
    };
    loop();
    return () => { running = false; cancelAnimationFrame(animFrameRef.current); };
  }, [draw]);

  // Handle tile click/hover
  const handleMouse = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const ts = state.zoom;
    const offsetX = canvas.width / 2 - state.cameraX * ts;
    const offsetY = canvas.height / 2 - state.cameraY * ts;

    const tileX = Math.floor((mx - offsetX) / ts);
    const tileY = Math.floor((my - offsetY) / ts);

    if (tileX >= 0 && tileX < MAP_SIZE && tileY >= 0 && tileY < MAP_SIZE) {
      const tile = { x: tileX, y: tileY };
      if (e.type === 'click') {
        onTileClick(tile);
      } else {
        onTileHover(tile);
      }
    }
  }, [state.zoom, state.cameraX, state.cameraY, onTileClick, onTileHover]);

  // Minimap click
  const handleMinimapClick = useCallback((e) => {
    const minimap = minimapRef.current;
    if (!minimap) return;
    const rect = minimap.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const scale = minimap.width / MAP_SIZE;

    const tileX = Math.floor(mx / scale);
    const tileY = Math.floor(my / scale);

    if (tileX >= 0 && tileX < MAP_SIZE && tileY >= 0 && tileY < MAP_SIZE) {
      onTileClick({ x: tileX, y: tileY, isMinimap: true });
    }
  }, [onTileClick]);

  return (
    <>
      <div className="canvas-container">
        <canvas
          ref={canvasRef}
          className="game-canvas"
          onClick={handleMouse}
          onMouseMove={handleMouse}
        />
      </div>
      <div className="minimap-container">
        <canvas
          ref={minimapRef}
          className="minimap-canvas"
          width={180}
          height={180}
          onClick={handleMinimapClick}
        />
      </div>
    </>
  );
}

// Named export for drawMinimap (used in useCallback above)
const drawMinmap = () => {};

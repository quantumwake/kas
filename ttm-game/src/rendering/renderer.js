import { MAP_SIZE, TILE_SIZE, TERRAIN, TERRAIN_COLORS, TILE, VEHICLE_DEFS, INDUSTRY_TYPES, TOWN_SIZES, CARGO_TYPES } from './constants.js';

// Offscreen canvas for caching terrain tiles
const tileCache = new Map();

function getTileCanvas(terrainType, surfaceType, featureType, elevation) {
  const key = `${terrainType}_${surfaceType}_${featureType}_${elevation > 0.3 ? 'hi' : 'lo'}`;
  if (tileCache.has(key)) return tileCache.get(key);

  const size = TILE_SIZE;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');

  // Base terrain color
  let baseColor = TERRAIN_COLORS[terrainType] || '#4a8c3f';
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, size, size);

  // Add slight variation
  const variation = ((terrainType * 7 + surfaceType * 13 + featureType * 31) % 20) - 10;
  if (variation !== 0) {
    ctx.fillStyle = `rgba(0,0,0,${Math.abs(variation) / 100})`;
    ctx.fillRect(0, 0, size, size);
  }

  // Draw surface (roads, rails, etc.)
  if (surfaceType === TILE.ROAD) {
    ctx.fillStyle = '#555555';
    ctx.fillRect(0, size / 2 - 2, size, 4);
    ctx.fillRect(size / 2 - 2, 0, 4, size);
    // Road markings
    ctx.fillStyle = '#ffff00';
    ctx.fillRect(size / 2 - 1, 0, 2, 2);
    ctx.fillRect(size / 2 - 1, size - 2, 2, 2);
  } else if (surfaceType === TILE.RAIL) {
    ctx.fillStyle = '#444444';
    ctx.fillRect(2, 0, 2, size);
    ctx.fillRect(size - 4, 0, 2, size);
    // Rails
    ctx.fillStyle = '#888888';
    ctx.fillRect(3, 0, 1, size);
    ctx.fillRect(size - 4, 0, 1, size);
    // Sleepers
    ctx.fillStyle = '#6b4226';
    for (let y = 0; y < size; y += 4) {
      ctx.fillRect(1, y, size - 2, 2);
    }
  } else if (surfaceType === TILE.STATION) {
    ctx.fillStyle = '#2196F3';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#1976D2';
    ctx.fillRect(1, 1, size - 2, size - 2);
    // Platform markings
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(2, 2, size - 4, 2);
    ctx.fillRect(2, size - 4, size - 4, 2);
  } else if (surfaceType === TILE.BUS_STOP) {
    ctx.fillStyle = '#FF9800';
    ctx.fillRect(size / 2 - 2, 0, 4, size);
    ctx.fillStyle = '#fff';
    ctx.fillRect(size / 2 - 1, 2, 2, size - 4);
  } else if (surfaceType === TILE.AIRPORT) {
    ctx.fillStyle = '#666666';
    ctx.fillRect(0, 0, size, size);
    // Runway markings
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, size / 2 - 1, size, 2);
    ctx.fillRect(size / 2 - 1, 0, 2, size);
  } else if (surfaceType === TILE.DOCK) {
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#654321';
    ctx.fillRect(0, 0, size, 3);
  } else if (surfaceType === TILE.BRIDGE) {
    ctx.fillStyle = '#999999';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#777777';
    ctx.fillRect(2, 0, size - 4, size);
  } else if (surfaceType === TILE.SIGNAL) {
    ctx.fillStyle = '#ff0000';
    ctx.fillRect(size / 2 - 2, 2, 4, size - 4);
    ctx.fillStyle = '#ffff00';
    ctx.fillRect(size / 2 - 1, size / 2 - 1, 2, 2);
  }

  // Draw features (trees, houses, industries)
  if (featureType === 1) { // Tree
    ctx.fillStyle = '#2d5a1e';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 2, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#1a3a10';
    ctx.beginPath();
    ctx.arc(size / 2 - 2, size / 2 - 3, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#4a2a0a';
    ctx.fillRect(size / 2 - 1, size / 2 + 1, 2, 4);
  } else if (featureType === 2) { // House
    ctx.fillStyle = '#d4a574';
    ctx.fillRect(size / 2 - 3, size / 2 - 2, 6, 6);
    ctx.fillStyle = '#8B4513';
    ctx.beginPath();
    ctx.moveTo(size / 2 - 4, size / 2 - 2);
    ctx.lineTo(size / 2, size / 2 - 6);
    ctx.lineTo(size / 2 + 4, size / 2 - 2);
    ctx.fill();
  } else if (featureType === 3) { // Industry
    ctx.fillStyle = '#666666';
    ctx.fillRect(size / 2 - 4, size / 2 - 3, 8, 6);
    ctx.fillStyle = '#333333';
    ctx.fillRect(size / 2 - 1, size / 2 - 6, 3, 4);
  }

  // Water animation shimmer
  if (terrainType === TERRAIN.WATER) {
    const shimmer = (elevation || 0) > -0.1 ? 'rgba(255,255,255,0.1)' : 'transparent';
    ctx.fillStyle = shimmer;
    ctx.fillRect(0, 0, size, size);
  }

  tileCache.set(key, canvas);
  return canvas;
}

// Draw a vehicle on canvas
export function drawVehicle(ctx, vehicle, x, y, tileSize) {
  const def = VEHICLE_DEFS[vehicle.defId];
  if (!def) return;

  const px = x * tileSize;
  const py = y * tileSize;
  const s = tileSize;

  ctx.save();

  if (def.cls === 'train') {
    // Draw train
    ctx.fillStyle = def.color;
    ctx.fillRect(px + 2, py + s / 2 - 3, s - 4, 6);
    ctx.fillStyle = '#333';
    ctx.fillRect(px + s / 2 - 2, py + s / 2 - 4, 4, 8);
    // Wheels
    ctx.fillStyle = '#222';
    ctx.beginPath();
    ctx.arc(px + 4, py + s / 2 + 3, 2, 0, Math.PI * 2);
    ctx.arc(px + s - 4, py + s / 2 + 3, 2, 0, Math.PI * 2);
    ctx.fill();
  } else if (def.cls === 'road') {
    // Draw bus/truck
    ctx.fillStyle = def.color;
    ctx.fillRect(px + s / 4, py + s / 4, s / 2, s / 2);
    ctx.fillStyle = '#333';
    ctx.fillRect(px + s / 4, py + s / 4, s / 2, 2);
    // Wheels
    ctx.fillStyle = '#111';
    ctx.beginPath();
    ctx.arc(px + s / 3, py + s * 0.7, 2, 0, Math.PI * 2);
    ctx.arc(px + s * 0.66, py + s * 0.7, 2, 0, Math.PI * 2);
    ctx.fill();
  } else if (def.cls === 'air') {
    // Draw plane
    ctx.fillStyle = def.color;
    ctx.beginPath();
    ctx.moveTo(px + s / 2, py + 2);
    ctx.lineTo(px + s - 4, py + s / 2);
    ctx.lineTo(px + s / 2, py + s - 2);
    ctx.lineTo(px + 4, py + s / 2);
    ctx.fill();
    // Wings
    ctx.fillStyle = '#ccc';
    ctx.fillRect(px + s / 2 - 1, py + s / 2 - 4, 2, 8);
  } else if (def.cls === 'water') {
    // Draw ship
    ctx.fillStyle = def.color;
    ctx.beginPath();
    ctx.moveTo(px + 2, py + s / 2);
    ctx.lineTo(px + s / 2, py + 2);
    ctx.lineTo(px + s - 2, py + s / 2);
    ctx.lineTo(px + s / 2, py + s - 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.fillRect(px + s / 2 - 2, py + s / 2 - 2, 4, 4);
  }

  // Cargo indicator
  if (vehicle.cargo && vehicle.cargo.length > 0) {
    const total = vehicle.cargo.reduce((sum, c) => sum + c.amount, 0);
    if (total > 0) {
      ctx.fillStyle = '#0f0';
      ctx.fillRect(px + s - 4, py + 1, 3, 3);
    }
  }

  ctx.restore();
}

// Draw minimap
export function drawMinimap(ctx, state, width, height) {
  const { terrain, surface, features, towns, industries } = state;
  const scale = width / MAP_SIZE;

  // Background
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, width, height);

  // Draw terrain (scaled down)
  const step = 4; // skip tiles for performance
  for (let y = 0; y < MAP_SIZE; y += step) {
    for (let x = 0; x < MAP_SIZE; x += step) {
      const idx = y * MAP_SIZE + x;
      ctx.fillStyle = TERRAIN_COLORS[terrain[idx]] || '#4a8c3f';
      ctx.fillRect(x * scale, y * scale, scale * step + 1, scale * step + 1);

      // Surface overlay
      if (surface[idx]) {
        if (surface[idx] === TILE.ROAD) ctx.fillStyle = '#888';
        else if (surface[idx] === TILE.RAIL) ctx.fillStyle = '#aaa';
        else if (surface[idx] === TILE.STATION) ctx.fillStyle = '#2196F3';
        else if (surface[idx] === TILE.AIRPORT) ctx.fillStyle = '#fff';
        else if (surface[idx] === TILE.DOCK) ctx.fillStyle = '#8B4513';
        ctx.fillRect(x * scale, y * scale, scale * step + 1, scale * step + 1);
      }
    }
  }

  // Draw towns
  for (const town of towns) {
    ctx.fillStyle = '#00ff00';
    ctx.fillRect(town.x * scale - 2, town.y * scale - 2, 5, 5);
  }

  // Draw industries
  for (const ind of industries) {
    ctx.fillStyle = '#ff0000';
    ctx.fillRect(ind.x * scale - 2, ind.y * scale - 2, 4, 4);
  }

  // Draw vehicles
  for (const v of state.vehicles) {
    const def = VEHICLE_DEFS[v.defId];
    ctx.fillStyle = def?.color || '#fff';
    ctx.fillRect(v.x * scale - 1, v.y * scale - 1, 3, 3);
  }

  // Draw camera viewport
  ctx.strokeStyle = '#ffff00';
  ctx.lineWidth = 2;
  const viewW = (32 / state.zoom) * scale;
  const viewH = (32 / state.zoom) * scale;
  ctx.strokeRect(
    state.cameraX * scale - viewW / 2,
    state.cameraY * scale - viewH / 2,
    viewW, viewH
  );
}

// Get the cached tile canvas
export function getTile(terrainType, surfaceType, featureType, elevation) {
  return getTileCanvas(terrainType, surfaceType, featureType, elevation);
}

// Render the visible map area
export function renderMap(ctx, state, canvasWidth, canvasHeight) {
  const { terrain, surface, features, elevation, towns, industries, vehicles, cameraX, cameraY, zoom } = state;
  const tileSize = Math.floor(TILE_SIZE * zoom);
  const viewTilesX = Math.ceil(canvasWidth / tileSize) + 2;
  const viewTilesY = Math.ceil(canvasHeight / tileSize) + 2;

  // Clear canvas
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  const offsetX = Math.floor(canvasWidth / 2);
  const offsetY = Math.floor(canvasHeight / 2);

  // Draw tiles
  for (let vy = -1; vy < viewTilesY; vy++) {
    for (let vx = -1; vx < viewTilesX; vx++) {
      const mapX = cameraX + vx - Math.floor(viewTilesX / 2);
      const mapY = cameraY + vy - Math.floor(viewTilesY / 2);

      if (mapX < 0 || mapX >= MAP_SIZE || mapY < 0 || mapY >= MAP_SIZE) continue;

      const idx = mapY * MAP_SIZE + mapX;
      const screenX = offsetX + vx * tileSize;
      const screenY = offsetY + vy * tileSize;

      // Draw cached tile
      const tileCanvas = getTile(terrain[idx], surface[idx], features[idx], elevation[idx]);
      ctx.drawImage(tileCanvas, screenX, screenY, tileSize, tileSize);
    }
  }

  // Draw town labels
  ctx.font = `${Math.max(10, 12 * zoom)}px sans-serif`;
  ctx.textAlign = 'center';
  for (const town of towns) {
    const screenX = offsetX + (town.x - cameraX + viewTilesX / 2) * tileSize;
    const screenY = offsetY + (town.y - cameraY + viewTilesY / 2) * tileSize;

    if (Math.abs(town.x - cameraX) < viewTilesX / 2 && Math.abs(town.y - cameraY) < viewTilesY / 2) {
      // Town name
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 3;
      ctx.strokeText(town.name, screenX, screenY - tileSize);
      ctx.fillText(town.name, screenX, screenY - tileSize);

      // Population
      ctx.font = `${Math.max(8, 9 * zoom)}px sans-serif`;
      ctx.fillStyle = '#cccccc';
      ctx.strokeText(`Pop: ${town.population}`, screenX, screenY - tileSize + 12);
      ctx.fillText(`Pop: ${town.population}`, screenX, screenY - tileSize + 12);
      ctx.font = `${Math.max(10, 12 * zoom)}px sans-serif`;
    }
  }

  // Draw industry labels
  for (const ind of industries) {
    const screenX = offsetX + (ind.x - cameraX + viewTilesX / 2) * tileSize;
    const screenY = offsetY + (ind.y - cameraY + viewTilesY / 2) * tileSize;

    if (Math.abs(ind.x - cameraX) < viewTilesX / 2 && Math.abs(ind.y - cameraY) < viewTilesY / 2) {
      const indDef = INDUSTRY_TYPES[ind.type];
      ctx.fillStyle = indDef.color;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.strokeText(ind.name, screenX, screenY - tileSize);
      ctx.fillText(ind.name, screenX, screenY - tileSize);
    }
  }

  // Draw vehicles
  for (const v of vehicles) {
    if (Math.abs(v.x - cameraX) < viewTilesX / 2 && Math.abs(v.y - cameraY) < viewTilesY / 2) {
      drawVehicle(ctx, v,
        offsetX + (v.x - cameraX + viewTilesX / 2),
        offsetY + (v.y - cameraY + viewTilesY / 2),
        tileSize
      );
    }
  }

  // Draw hover highlight
  if (state.hoveredTile) {
    const { x, y } = state.hoveredTile;
    const screenX = offsetX + (x - cameraX + viewTilesX / 2) * tileSize;
    const screenY = offsetY + (y - cameraY + viewTilesY / 2) * tileSize;
    ctx.strokeStyle = '#ffff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(screenX, screenY, tileSize, tileSize);
  }
}

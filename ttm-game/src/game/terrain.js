// ===== SIMPLEX NOISE (compact implementation) =====

class SimplexNoise {
  constructor(seed = Math.random()) {
    this.grad3 = [
      [1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
      [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
      [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]
    ];
    this.p = [];
    for (let i = 0; i < 256; i++) this.p[i] = i;
    // Fisher-Yates shuffle with seed
    let s = seed * 65536;
    for (let i = 255; i > 0; i--) {
      s = (s * 16807 + 12345) % 2147483647;
      const j = Math.floor((s / 2147483647) * (i + 1));
      [this.p[i], this.p[j]] = [this.p[j], this.p[i]];
    }
    this.perm = new Array(512);
    for (let i = 0; i < 512; i++) this.perm[i] = this.p[i & 255];
  }

  dot3(g, x, y) { return g[0]*x + g[1]*y; }

  noise2D(xin, yin) {
    const F2 = 0.5 * (Math.sqrt(3) - 1);
    const G2 = (3 - Math.sqrt(3)) / 6;
    const s = (xin + yin) * F2;
    const i = Math.floor(xin + s);
    const j = Math.floor(yin + s);
    const t = (i + j) * G2;
    const X0 = i - t;
    const Y0 = j - t;
    const x0 = xin - X0;
    const y0 = yin - Y0;
    let i1, j1;
    if (x0 > y0) { i1 = 1; j1 = 0; }
    else { i1 = 0; j1 = 1; }
    const x1 = x0 - i1 + G2;
    const y1 = y0 - j1 + G2;
    const x2 = x0 - 1 + 2 * G2;
    const y2 = y0 - 1 + 2 * G2;
    const ii = i & 255;
    const jj = j & 255;
    const gi0 = this.perm[ii + this.perm[jj]] % 12;
    const gi1 = this.perm[ii + i1 + this.perm[jj + j1]] % 12;
    const gi2 = this.perm[ii + 1 + this.perm[jj + 1]] % 12;
    let n0, n1, n2;
    let t0 = 0.5 - x0*x0 - y0*y0;
    n0 = t0 < 0 ? 0 : (t0 *= t0, t0 * t0 * this.dot3(this.grad3[gi0], x0, y0));
    let t1 = 0.5 - x1*x1 - y1*y1;
    n1 = t1 < 0 ? 0 : (t1 *= t1, t1 * t1 * this.dot3(this.grad3[gi1], x1, y1));
    let t2 = 0.5 - x2*x2 - y2*y2;
    n2 = t2 < 0 ? 0 : (t2 *= t2, t2 * t2 * this.dot3(this.grad3[gi2], x2, y2));
    return 60 * (n0 + n1 + n2);
  }

  octave2D(x, y, octaves, persistence) {
    let total = 0;
    let frequency = 1;
    let amplitude = 1;
    let maxValue = 0;
    for (let i = 0; i < octaves; i++) {
      total += this.noise2D(x * frequency, y * frequency) * amplitude;
      maxValue += amplitude;
      amplitude *= persistence;
      frequency *= 2;
    }
    return total / maxValue;
  }
}

// ===== MAP GENERATION =====

import { MAP_SIZE, TERRAIN, SURFACE, INDUSTRY_TYPES, TOWN_STAGES } from './constants.js';

function generateMap(seed) {
  const noise = new SimplexNoise(seed);
  const waterNoise = new SimplexNoise(seed + 1000);
  const detailNoise = new SimplexNoise(seed + 2000);

  // Create elevation map
  const elevation = new Float32Array(MAP_SIZE * MAP_SIZE);
  // Create moisture map
  const moisture = new Float32Array(MAP_SIZE * MAP_SIZE);

  for (let y = 0; y < MAP_SIZE; y++) {
    for (let x = 0; x < MAP_SIZE; x++) {
      const nx = x / MAP_SIZE;
      const ny = y / MAP_SIZE;

      // Multi-octave noise for elevation
      const elev = noise.octave2D(nx * 6, ny * 6, 5, 0.5);
      // Make edges more mountainous
      const distFromCenter = Math.sqrt(
        Math.pow((nx - 0.5) * 2, 2) + Math.pow((ny - 0.5) * 2, 2)
      );
      const edgeFactor = Math.max(0, (distFromCenter - 0.3) * 2);
      elevation[y * MAP_SIZE + x] = elev * 0.6 + edgeFactor * 0.4;

      // Moisture for biome variation
      moisture[y * MAP_SIZE + x] = waterNoise.octave2D(nx * 8, ny * 8, 3, 0.5);
    }
  }

  // Create tiles
  const tiles = new Array(MAP_SIZE * MAP_SIZE);
  const waterLevel = -0.05;

  for (let y = 0; y < MAP_SIZE; y++) {
    for (let x = 0; x < MAP_SIZE; x++) {
      const i = y * MAP_SIZE + x;
      const elev = elevation[i];
      const moist = moisture[i];
      const detail = detailNoise.noise2D(x * 0.05, y * 0.05) * 0.1;

      let terrain;
      if (elev < waterLevel - 0.1) {
        terrain = TERRAIN.WATER;
      } else if (elev < waterLevel) {
        terrain = TERRAIN.WATER; // shallow water
      } else if (elev < waterLevel + 0.05) {
        terrain = TERRAIN.GRASS; // beach/flat
      } else if (elev < 0.2) {
        terrain = moist > 0.1 ? TERRAIN.GRASS : TERRAIN.DESERT;
      } else if (elev < 0.35) {
        terrain = TERRAIN.HILLS;
      } else if (elev < 0.5) {
        terrain = TERRAIN.MOUNTAIN;
      } else {
        terrain = moist > 0 ? TERRAIN.SNOW : TERRAIN.MOUNTAIN;
      }

      tiles[i] = {
        terrain,
        surface: SURFACE.NONE,
        elevation: elev + detail,
        hasTree: terrain === TERRAIN.GRASS && detail > 0.05 && Math.random() < 0.15,
        treeType: Math.random() < 0.3 ? 1 : 0,
        industry: null,
        town: null,
        building: null,
        // For stations/terminals
        stationId: null,
        // Height for 3D effect
        height: Math.max(0, (elev - waterLevel) * 8),
      };
    }
  }

  return tiles;
}

// ===== TOWN GENERATION =====

function findFlatArea(tiles, minElev, maxElev, minSize) {
  // Find connected flat areas
  const candidates = [];
  for (let y = 32; y < MAP_SIZE - 32; y += 16) {
    for (let x = 32; x < MAP_SIZE - 32; x += 16) {
      const i = y * MAP_SIZE + x;
      if (tiles[i].terrain === TERRAIN.GRASS || tiles[i].terrain === TERRAIN.DESERT) {
        if (tiles[i].elevation >= minElev && tiles[i].elevation <= maxElev) {
          // Count flat neighbors
          let count = 0;
          for (let dy = -8; dy <= 8; dy++) {
            for (let dx = -8; dx <= 8; dx++) {
              const ni = (y + dy) * MAP_SIZE + (x + dx);
              if (ni >= 0 && ni < tiles.length) {
                const t = tiles[ni];
                if ((t.terrain === TERRAIN.GRASS || t.terrain === TERRAIN.DESERT) &&
                    t.elevation >= minElev - 0.05 && t.elevation <= maxElev + 0.05) {
                  count++;
                }
              }
            }
          }
          if (count >= minSize) {
            candidates.push({ x, y, score: count });
          }
        }
      }
    }
  }
  return candidates.sort((a, b) => b.score - a.score);
}

function generateTowns(tiles, count) {
  const candidates = findFlatArea(tiles, -0.02, 0.15, 80);
  const towns = [];
  const taken = new Set();

  for (const c of candidates) {
    if (towns.length >= count) break;
    // Check distance from existing towns
    let tooClose = false;
    for (const town of towns) {
      const dist = Math.sqrt(
        Math.pow(town.x - c.x, 2) + Math.pow(town.y - c.y, 2)
      );
      if (dist < 80) { tooClose = true; break; }
    }
    if (tooClose) continue;

    const key = `${c.x},${c.y}`;
    if (taken.has(key)) continue;
    taken.add(key);

    // Generate town buildings
    const buildings = [];
    const radius = 15 + Math.random() * 10;
    let houseCount = 0;
    const targetHouses = 8 + Math.floor(Math.random() * 12);

    for (let dy = -radius; dy <= radius; dy += 2) {
      for (let dx = -radius; dx <= radius; dx += 2) {
        if (houseCount >= targetHouses) break;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > radius) continue;
        if (Math.random() > (1 - dist / radius) * 0.6) continue;

        const tx = c.x + dx;
        const ty = c.y + dy;
        const i = ty * MAP_SIZE + tx;
        if (tx < 0 || tx >= MAP_SIZE || ty < 0 || ty >= MAP_SIZE) continue;
        if (tiles[i].terrain !== TERRAIN.GRASS && tiles[i].terrain !== TERRAIN.DESERT) continue;
        if (tiles[i].elevation > 0.15) continue;

        const buildingType = Math.random() < 0.15 ? 'townhall' :
                             Math.random() < 0.1 ? 'shop' : 'house';
        const building = {
          type: buildingType,
          x: tx, y: ty,
          color: buildingType === 'house' ? ['#8b4513','#a0522d','#cd853f','#d2691e'][Math.floor(Math.random()*4)] :
                 buildingType === 'townhall' ? '#b22222' : '#daa520',
          size: buildingType === 'townhall' ? 2 : 1,
        };
        buildings.push(building);
        tiles[i].building = buildings.length - 1;
        tiles[i].hasTree = false;
        houseCount++;
      }
    }

    // Generate roads between buildings
    for (let i = 0; i < buildings.length - 1; i++) {
      connectBuildings(tiles, buildings[i], buildings[i + 1]);
    }

    const town = {
      id: towns.length,
      name: generateTownName(),
      x: c.x,
      y: c.y,
      population: 40 + Math.floor(Math.random() * 20),
      stage: 0,
      buildings,
      passengersWaiting: 0,
      mailWaiting: 0,
      happiness: 50,
    };

    // Mark tiles with town reference
    for (const b of buildings) {
      const i = b.y * MAP_SIZE + b.x;
      tiles[i].town = town.id;
    }

    towns.push(town);
  }

  return towns;
}

function connectBuildings(tiles, a, b) {
  // Simple path: go horizontal then vertical (L-shape)
  let x = a.x;
  const y1 = a.y;
  const y2 = b.y;

  while (x !== b.x) {
    const i = y1 * MAP_SIZE + x;
    if (tiles[i].terrain === TERRAIN.GRASS || tiles[i].terrain === TERRAIN.DESERT) {
      if (tiles[i].surface === SURFACE.NONE) {
        tiles[i].surface = SURFACE.ROAD;
      }
    }
    x += b.x > x ? 1 : -1;
  }

  x = b.x;
  while (y1 !== y2) {
    const i = y1 * MAP_SIZE + x;
    if (tiles[i].terrain === TERRAIN.GRASS || tiles[i].terrain === TERRAIN.DESERT) {
      if (tiles[i].surface === SURFACE.NONE) {
        tiles[i].surface = SURFACE.ROAD;
      }
    }
    y1 += y2 > y1 ? 1 : -1;
  }
}

// Town name generation
const townPrefixes = ['New', 'Fort', 'Saint', 'Lake', 'Port', 'East', 'West', 'North', 'South', 'Little', 'Big', 'Old'];
const townRoots = ['ton', 'ville', 'burg', 'field', 'worth', 'port', 'side', 'dale', 'wood', 'brook', 'haven', 'view', 'crest', 'ridge', 'ton', 'ton'];
const townNames = ['Springfield', 'Ridgewood', 'Lakewood', 'Fairview', 'Millfield', 'Oakdale', 'Pineville', 'Cedarburg', 'Mapleton', 'Elmsworth', 'Ashford', 'Bridgeton', 'Claremont', 'Doverton', 'Edgewater', 'Falconridge', 'Greenfield', 'Hawthorne', 'Iverson', 'Jasper', 'Kingsley', 'Linden', 'Madison', 'Nashville', 'Oakhaven', 'Parkside', 'Quincy', 'Riverside', 'Summertown', 'Thornbury', 'Unionville', 'Valleyford', 'Woodstock'];

function generateTownName() {
  if (Math.random() < 0.5) {
    return townNames[Math.floor(Math.random() * townNames.length)];
  }
  return townPrefixes[Math.floor(Math.random() * townPrefixes.length)] +
         townRoots[Math.floor(Math.random() * townRoots.length)];
}

// ===== INDUSTRY GENERATION =====

function generateIndustries(tiles, towns, count) {
  const industries = [];
  const usedTypes = new Set();

  // First place resource industries (no road needed)
  const resourceTypes = [0, 1, 2, 3, 4, 5]; // Coal, Iron, Quarry, Lumber, Farm, Oil
  for (const type of resourceTypes) {
    const spots = findIndustrySpots(tiles, towns, type, 1);
    for (const spot of spots) {
      const industry = createIndustry(tiles, spot, type, industries.length);
      if (industry) {
        industries.push(industry);
        usedTypes.add(type);
      }
    }
  }

  // Then place manufacturing industries (need road connection to resource)
  const manufacturingTypes = [6, 7, 8, 9, 10, 11];
  for (const type of manufacturingTypes) {
    const def = INDUSTRY_TYPES[type];
    // Find a resource that produces what this needs
    const neededCargo = def.consumes;
    const sourceIndustries = industries.filter(ind => ind.production === neededCargo);
    if (sourceIndustries.length > 0) {
      const spots = findIndustrySpots(tiles, towns, type, 1, sourceIndustries[0]);
      for (const spot of spots) {
        const industry = createIndustry(tiles, spot, type, industries.length);
        if (industry) {
          industries.push(industry);
        }
      }
    }
  }

  return industries;
}

function findIndustrySpots(tiles, towns, type, count, nearIndustry = null) {
  const def = INDUSTRY_TYPES[type];
  const spots = [];
  const requiredTerrain = type === 0 || type === 1 ? [TERRAIN.HILLS, TERRAIN.MOUNTAIN] : // mines need hills
                          type === 3 ? [TERRAIN.GRASS] : // lumber needs forest
                          type === 5 ? [TERRAIN.DESERT] : // oil needs desert
                          [TERRAIN.GRASS, TERRAIN.DESERT];

  const candidates = [];
  for (let y = 20; y < MAP_SIZE - 20; y += 8) {
    for (let x = 20; x < MAP_SIZE - 20; x += 8) {
      const i = y * MAP_SIZE + x;
      if (!requiredTerrain.includes(tiles[i].terrain)) continue;
      if (tiles[i].elevation > 0.2 || tiles[i].elevation < -0.05) continue;

      // Check not too close to towns
      let tooCloseToTown = false;
      for (const town of towns) {
        const dist = Math.sqrt(Math.pow(town.x - x, 2) + Math.pow(town.y - y, 2));
        if (dist < 30) { tooCloseToTown = true; break; }
      }
      if (tooCloseToTown) continue;

      // Check not too close to other industries
      let tooCloseToIndustry = false;
      for (const ind of spots) {
        const dist = Math.sqrt(Math.pow(ind.x - x, 2) + Math.pow(ind.y - y, 2));
        if (dist < 25) { tooCloseToIndustry = true; break; }
      }
      if (tooCloseToIndustry) continue;

      // If needs to be near a specific industry, check distance
      if (nearIndustry) {
        const dist = Math.sqrt(Math.pow(nearIndustry.x - x, 2) + Math.pow(nearIndustry.y - y, 2));
        if (dist > 120) continue; // must be reachable
      }

      candidates.push({ x, y, score: Math.random() });
    }
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates.slice(0, count);
}

function createIndustry(tiles, spot, type, id) {
  const def = INDUSTRY_TYPES[type];
  const size = 3 + Math.floor(Math.random() * 3);

  // Check if we can place it
  for (let dy = -size; dy <= size; dy++) {
    for (let dx = -size; dx <= size; dx++) {
      const tx = spot.x + dx;
      const ty = spot.y + dy;
      if (tx < 0 || tx >= MAP_SIZE || ty < 0 || ty >= MAP_SIZE) return null;
      const i = ty * MAP_SIZE + tx;
      if (tiles[i].terrain === TERRAIN.WATER) return null;
      if (tiles[i].elevation > 0.2) return null;
    }
  }

  const industry = {
    id,
    type,
    name: def.name,
    x: spot.x,
    y: spot.y,
    size,
    production: def.produces,
    storage: 0,
    maxStorage: 100,
    productionRate: 2 + Math.floor(Math.random() * 3),
    needsCargo: def.consumes || null,
    isActive: true,
    connected: false,
  };

  // Mark tiles
  for (let dy = -size; dy <= size; dy++) {
    for (let dx = -size; dx <= size; dx++) {
      const tx = spot.x + dx;
      const ty = spot.y + dy;
      const i = ty * MAP_SIZE + tx;
      tiles[i].industry = id;
      tiles[i].hasTree = false;
      tiles[i].building = id;
    }
  }

  // Build road to it if needed
  if (def.needsRoad) {
    // Road from center
    const roadDir = Math.floor(Math.random() * 4);
    for (let d = size; d < size + 15; d++) {
      let rx, ry;
      if (roadDir === 0) { rx = spot.x + d; ry = spot.y; }
      else if (roadDir === 1) { rx = spot.x - d; ry = spot.y; }
      else if (roadDir === 2) { rx = spot.x; ry = spot.y + d; }
      else { rx = spot.x; ry = spot.y - d; }
      if (rx >= 0 && rx < MAP_SIZE && ry >= 0 && ry < MAP_SIZE) {
        const i = ry * MAP_SIZE + rx;
        if (tiles[i].terrain !== TERRAIN.WATER && tiles[i].elevation <= 0.15) {
          tiles[i].surface = SURFACE.ROAD;
        } else break;
      } else break;
    }
  }

  return industry;
}

// ===== STATION / TERMINAL MANAGEMENT =====

let nextStationId = 0;

function createStation(tiles, x, y, type) {
  const id = nextStationId++;
  const station = {
    id,
    type,
    x, y,
    name: `${TOOL_NAMES[type].replace('Build ', '').replace('Build ', '')} ${id + 1}`,
    waitingPassengers: 0,
    waitingMail: 0,
    waitingCargo: {},
  };

  // Mark tiles based on station type
  const markTile = (tx, ty, surface) => {
    if (tx < 0 || tx >= MAP_SIZE || ty < 0 || ty >= MAP_SIZE) return;
    const i = ty * MAP_SIZE + tx;
    tiles[i].surface = surface;
    tiles[i].stationId = id;
    tiles[i].hasTree = false;
  };

  switch (type) {
    case TOOL.BUILD_TRAIN_STATION:
      for (let dx = 0; dx < 8; dx++) markTile(x + dx, y, SURFACE.STATION_TRAIN);
      break;
    case TOOL.BUILD_BUS_STOP:
      markTile(x, y, SURFACE.STATION_BUS);
      markTile(x + 1, y, SURFACE.STATION_BUS);
      break;
    case TOOL.BUILD_TRUCK_STOP:
      markTile(x, y, SURFACE.STATION_TRUCK);
      markTile(x + 1, y, SURFACE.STATION_TRUCK);
      break;
    case TOOL.BUILD_AIRPORT:
      for (let dy = -5; dy <= 5; dy++) {
        for (let dx = -5; dx <= 5; dx++) {
          markTile(x + dx, y + dy, SURFACE.AIRPORT);
        }
      }
      break;
    case TOOL.BUILD_DOCK:
      for (let dx = 0; dx < 3; dx++) markTile(x + dx, y, SURFACE.DOCK);
      break;
  }

  return station;
}

// ===== EXPORT =====

export {
  SimplexNoise,
  generateMap,
  generateTowns,
  generateIndustries,
  createStation,
};

// ===== TERRAIN / MAP GENERATION =====
// Uses Simplex noise for procedural generation

import { MAP_SIZE, TERRAIN } from './constants.js';

// ---- Simplex Noise (compact 2D) ----
class SimplexNoise {
  constructor(seed = Math.random()) {
    this.grad3 = [
      [1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
      [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
      [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]
    ];
    this.p = [];
    for (let i = 0; i < 256; i++) this.p[i] = i;
    let s = seed * 65536 | 0;
    for (let i = 255; i > 0; i--) {
      s = (s * 16807 + 12345) % 2147483647;
      const j = (s / 2147483647 * (i + 1)) | 0;
      [this.p[i], this.p[j]] = [this.p[j], this.p[i]];
    }
    this.perm = new Array(512);
    for (let i = 0; i < 512; i++) this.perm[i] = this.p[i & 255];
  }
  noise2D(xin, yin) {
    const F2 = 0.5 * (Math.sqrt(3) - 1), G2 = (3 - Math.sqrt(3)) / 6;
    const s = (xin + yin) * F2, i = Math.floor(xin + s), j = Math.floor(yin + s);
    const t = (i + j) * G2, X0 = i - t, Y0 = j - t;
    const x0 = xin - X0, y0 = yin - Y0;
    const i1 = x0 > y0 ? 1 : 0, j1 = x0 > y0 ? 0 : 1;
    const x1 = x0 - i1 + G2, y1 = y0 - j1 + G2;
    const x2 = x0 - 1 + 2 * G2, y2 = y0 - 1 + 2 * G2;
    const ii = i & 255, jj = j & 255;
    const gi0 = this.perm[ii + this.perm[jj]] % 12;
    const gi1 = this.perm[ii + i1 + this.perm[jj + j1]] % 12;
    const gi2 = this.perm[ii + 1 + this.perm[jj + 1]] % 12;
    let n0, n1, n2;
    let t0 = 0.5 - x0*x0 - y0*y0; n0 = t0 < 0 ? 0 : (t0 *= t0, t0*t0 * (this.grad3[gi0][0]*x0 + this.grad3[gi0][1]*y0));
    let t1 = 0.5 - x1*x1 - y1*y1; n1 = t1 < 0 ? 0 : (t1 *= t1, t1*t1 * (this.grad3[gi1][0]*x1 + this.grad3[gi1][1]*y1));
    let t2 = 0.5 - x2*x2 - y2*y2; n2 = t2 < 0 ? 0 : (t2 *= t2, t2*t2 * (this.grad3[gi2][0]*x2 + this.grad3[gi2][1]*y2));
    return 60 * (n0 + n1 + n2);
  }
  octave2D(x, y, octaves, persistence) {
    let total = 0, frequency = 1, amplitude = 1, maxValue = 0;
    for (let i = 0; i < octaves; i++) {
      total += this.noise2D(x * frequency, y * frequency) * amplitude;
      maxValue += amplitude; amplitude *= persistence; frequency *= 2;
    }
    return total / maxValue;
  }
}

// ---- Map Generation ----

export function generateMap(seed) {
  const noise = new SimplexNoise(seed);
  const moistureNoise = new SimplexNoise(seed + 1000);
  const detailNoise = new SimplexNoise(seed + 2000);

  const terrain = new Uint8Array(MAP_SIZE * MAP_SIZE);
  const features = new Uint8Array(MAP_SIZE * MAP_SIZE);
  const elevation = new Float32Array(MAP_SIZE * MAP_SIZE);

  const waterLevel = -0.05;

  for (let y = 0; y < MAP_SIZE; y++) {
    for (let x = 0; x < MAP_SIZE; x++) {
      const i = y * MAP_SIZE + x;
      const nx = x / MAP_SIZE, ny = y / MAP_SIZE;

      // Elevation with edge mountains
      const elev = noise.octave2D(nx * 6, ny * 6, 5, 0.5);
      const distFromCenter = Math.sqrt(Math.pow((nx - 0.5) * 2, 2) + Math.pow((ny - 0.5) * 2, 2));
      const edgeFactor = Math.max(0, (distFromCenter - 0.3) * 2);
      const finalElev = elev * 0.6 + edgeFactor * 0.4;
      elevation[i] = finalElev;

      const moist = moistureNoise.octave2D(nx * 8, ny * 8, 3, 0.5);
      const detail = detailNoise.noise2D(x * 0.05, y * 0.05) * 0.1;

      // Determine terrain
      if (finalElev < waterLevel) {
        terrain[i] = TERRAIN.WATER;
      } else if (finalElev < waterLevel + 0.05) {
        terrain[i] = TERRAIN.GRASS;
      } else if (finalElev < 0.2) {
        terrain[i] = moist > 0.1 ? TERRAIN.GRASS : TERRAIN.DESERT;
      } else if (finalElev < 0.35) {
        terrain[i] = TERRAIN.HILLS;
      } else if (finalElev < 0.5) {
        terrain[i] = TERRAIN.MOUNTAIN;
      } else {
        terrain[i] = moist > 0 ? TERRAIN.SNOW : TERRAIN.MOUNTAIN;
      }

      // Features: trees on grassland
      if (terrain[i] === TERRAIN.GRASS && detail > 0.05 && Math.random() < 0.12) {
        features[i] = 1; // tree
      }
    }
  }

  return { terrain, features, elevation };
}

// ---- Find flat area for town/industry placement ----

export function findFlatArea(terrain, size, minElev, maxElev, rngSeed) {
  const rng = (s) => { s = (s * 16807) % 2147483647; return (s % 2147483647) / 2147483647; };
  let s = rngSeed | 0;

  // Scan in a spiral from center-ish
  const candidates = [];
  const step = 16;
  for (let y = 32; y < size - 32; y += step) {
    for (let x = 32; x < size - 32; x += step) {
      const i = y * size + x;
      if (terrain[i] !== TERRAIN.GRASS && terrain[i] !== TERRAIN.DESERT) continue;
      if (elevationAt(terrain, size, x, y) === null) continue;

      // Check flatness in radius
      let flatCount = 0;
      const radius = 10;
      for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
          const ni = (y + dy) * size + (x + dx);
          if (ni >= 0 && ni < terrain.length) {
            if (terrain[ni] === TERRAIN.GRASS || terrain[ni] === TERRAIN.DESERT) {
              flatCount++;
            }
          }
        }
      }
      if (flatCount > 60) {
        candidates.push({ x, y, score: flatCount + rng(s) * 20 });
        s = (s * 16807) % 2147483647;
      }
    }
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates.length > 0 ? candidates[0] : null;
}

// Helper: get elevation or null if water
function elevationAt(terrain, size, x, y) {
  if (x < 0 || x >= size || y < 0 || y >= size) return null;
  return terrain[y * size + x] === TERRAIN.WATER ? null : 0;
}

// ---- Find water edge for docks ----

export function findWaterEdge(terrain, size, rngSeed) {
  const rng = (s) => { s = (s * 16807) % 2147483647; return (s % 2147483647) / 2147483647; };
  let s = rngSeed | 0;

  const candidates = [];
  const step = 16;
  for (let y = 32; y < size - 32; y += step) {
    for (let x = 32; x < size - 32; x += step) {
      const i = y * size + x;
      if (terrain[i] !== TERRAIN.WATER) continue;

      // Check if adjacent to land
      let hasLand = false;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const ni = (y + dy) * size + (x + dx);
          if (ni >= 0 && ni < terrain.length && terrain[ni] !== TERRAIN.WATER) {
            hasLand = true;
          }
        }
      }
      if (hasLand) {
        candidates.push({ x, y, score: rng(s) });
        s = (s * 16807) % 2147483647;
      }
    }
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates.length > 0 ? candidates[0] : null;
}

// ---- Town name generation ----
const townNames = ['Springfield','Riverside','Lakewood','Fairview','Oakdale','Maplewood',
  'Cedarburg','Brookfield','Pineville','Ashford','Bridgeton','Edgewater',
  'Greenfield','Hawthorne','Kingsley','Madison','Parkside','Riverside',
  'Summertown','Thornbury','Valleyford','Woodstock','Claremont','Doverton'];

export function generateTownName(index, rngSeed) {
  let s = rngSeed + index * 1000;
  s = (s * 16807) % 2147483647;
  return townNames[(s % townNames.length)];
}

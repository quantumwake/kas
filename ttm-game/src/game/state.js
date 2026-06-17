import {
  MAP_SIZE, TERRAIN, TILE, CARGO_TYPES, INDUSTRY_TYPES,
  VEHICLE_DEFS, VEHICLE_CLASSES, TOWN_SIZES, TOOLS,
  STARTING_MONEY, MAX_LOAN, LOAN_STEP, INTEREST_RATE,
  START_YEAR, END_YEAR, GAME_SPEED, BUILD_COSTS
} from './constants.js';
import { generateMap, findFlatArea, findWaterEdge } from './terrain.js';

// Create a new game state
export function createNewGame(seed = 42, difficulty = 'normal') {
  const mapData = generateMap(seed);
  const towns = [];
  const industries = [];
  let rng = seed + 5000;

  // Place towns
  const townNames = ['Springfield', 'Riverside', 'Lakewood', 'Fairview', 'Oakdale', 'Maplewood', 'Cedarburg', 'Brookfield'];
  for (let i = 0; i < 6; i++) {
    const loc = findFlatArea(mapData.terrain, MAP_SIZE, 8, rng + i * 1000);
    if (loc) {
      rng = (rng * 16807) % 2147483647;
      const town = {
        id: i,
        name: townNames[i] || `Town ${i}`,
        x: loc.x,
        y: loc.y,
        population: 50 + (rng % 60),
        cargo: {},
        passengers: [],
        serviceRating: 50,
      };
      // Mark town tiles
      for (let dy = -5; dy <= 5; dy++) {
        for (let dx = -5; dx <= 5; dx++) {
          if (dx * dx + dy * dy <= 36) {
            const idx = (loc.y + dy) * MAP_SIZE + (loc.x + dx);
            if (mapData.terrain[idx] === TERRAIN.GRASS) {
              mapData.features[idx] = 2; // house
            }
          }
        }
      }
      towns.push(town);
    }
  }

  // Place industries
  const availableIndustries = INDUSTRY_TYPES.filter(ind => ind.minYear <= START_YEAR);
  for (let i = 0; i < 8 && i < availableIndustries.length; i++) {
    const loc = findFlatArea(mapData.terrain, MAP_SIZE, 5, rng + i * 2000);
    if (loc) {
      rng = (rng * 16807) % 2147483647;
      const indDef = availableIndustries[i % availableIndustries.length];
      const industry = {
        id: i,
        type: indDef.id,
        name: indDef.name,
        x: loc.x,
        y: loc.y,
        cargo: {},
        needsCargo: indDef.consumes ? {} : null,
        produces: indDef.produces,
        storage: 0,
        maxStorage: 100,
        active: true,
      };
      // Mark industry tiles
      for (let dy = -3; dy <= 3; dy++) {
        for (let dx = -3; dx <= 3; dx++) {
          const idx = (loc.y + dy) * MAP_SIZE + (loc.x + dx);
          if (mapData.terrain[idx] === TERRAIN.GRASS) {
            mapData.features[idx] = 3; // industry
          }
        }
      }
      industries.push(industry);
    }
  }

  // Place docks near water
  const docks = [];
  for (let i = 0; i < 3; i++) {
    const loc = findWaterEdge(mapData.terrain, MAP_SIZE, rng + i * 3000);
    if (loc) {
      docks.push({ id: i, x: loc.x, y: loc.y });
    }
  }

  // Starting money based on difficulty
  const moneyMult = difficulty === 'easy' ? 1.5 : difficulty === 'hard' ? 0.7 : 1;

  return {
    // Map
    terrain: mapData.terrain,
    features: mapData.features,
    elevation: mapData.elevation,
    surface: new Uint8Array(MAP_SIZE * MAP_SIZE), // roads, rails, etc.
    stationMap: new Uint8Array(MAP_SIZE * MAP_SIZE), // station IDs

    // Towns & Industries
    towns,
    industries,
    docks,
    airports: [],

    // Vehicles
    vehicles: [],
    nextVehicleId: 0,

    // Economy
    money: Math.floor(STARTING_MONEY * moneyMult),
    loan: 0,
    monthlyIncome: 0,
    monthlyExpenses: 0,
    monthlyProfit: [], // last 24 months

    // Game time
    date: new Date(START_YEAR, 0, 1),
    dateTicks: 0, // ticks since start
    gameSpeed: GAME_SPEED.NORMAL,
    paused: false,

    // Player
    selectedTool: TOOLS.CURSOR,
    buildMode: null,
    cameraX: Math.floor(MAP_SIZE / 2),
    cameraY: Math.floor(MAP_SIZE / 2),
    zoom: 2,
    selectedVehicle: null,
    hoveredTile: null,

    // Stats
    totalPassengers: 0,
    totalCargo: 0,
    reputation: 50,

    // UI state (not saved)
    showPanel: null, // 'vehicle', 'economy', 'settings', 'saveload', 'info'
    notifications: [],
  };
}

// Game actions
export const ACTIONS = {
  TICK: 'TICK',
  BUILD: 'BUILD',
  DEMOLISH: 'DEMOLISH',
  BUY_VEHICLE: 'BUY_VEHICLE',
  SCRAP_VEHICLE: 'SCRAP_VEHICLE',
  MOVE_VEHICLE: 'MOVE_VEHICLE',
  CHANGE_TOOL: 'CHANGE_TOOL',
  CHANGE_SPEED: 'CHANGE_SPEED',
  TOGGLE_PAUSE: 'TOGGLE_PAUSE',
  MOVE_CAMERA: 'MOVE_CAMERA',
  ZOOM: 'ZOOM',
  TAKE_LOAN: 'TAKE_LOAN',
  REPAY_LOAN: 'REPAY_LOAN',
  SHOW_PANEL: 'SHOW_PANEL',
  HIDE_PANEL: 'HIDE_PANEL',
  SELECT_VEHICLE: 'SELECT_VEHICLE',
  LOAD_GAME: 'LOAD_GAME',
  NEW_GAME: 'NEW_GAME',
};

// Pathfinding - simple BFS
export function findPath(surface, terrain, startX, startY, endX, endY, tileType, maxDist = 500) {
  if (startX === endX && startY === endY) return [];

  const visited = new Uint8Array(MAP_SIZE * MAP_SIZE);
  const parent = new Int32Array(MAP_SIZE * MAP_SIZE * 2); // store parent as packed coords
  const queue = [{ x: startX, y: startY, dist: 0 }];
  visited[startY * MAP_SIZE + startX] = 1;

  const dirs = [[0,1],[0,-1],[1,0],[-1,0]];
  let found = false;

  while (queue.length > 0) {
    const { x, y, dist } = queue.shift();
    if (dist > maxDist) break;

    if (x === endX && y === endY) {
      found = true;
      break;
    }

    for (const [dx, dy] of dirs) {
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || nx >= MAP_SIZE || ny < 0 || ny >= MAP_SIZE) continue;
      const nIdx = ny * MAP_SIZE + nx;
      if (visited[nIdx]) continue;

      // Check if can traverse
      let canPass = false;
      if (tileType === TILE.RAIL) {
        canPass = surface[nIdx] === TILE.RAIL || surface[nIdx] === TILE.STATION || surface[nIdx] === TILE.SIGNAL;
      } else if (tileType === TILE.ROAD) {
        canPass = surface[nIdx] === TILE.ROAD || surface[nIdx] === TILE.STATION ||
                  surface[nIdx] === TILE.BUS_STOP || surface[nIdx] === TILE.TRUCK_STOP;
      } else if (tileType === TILE.BRIDGE) {
        canPass = surface[nIdx] === TILE.BRIDGE || surface[nIdx] === TILE.RAIL;
      }

      if (canPass) {
        visited[nIdx] = 1;
        parent[nIdx * 2] = x;
        parent[nIdx * 2 + 1] = y;
        queue.push({ x: nx, y: ny, dist: dist + 1 });
      }
    }
  }

  if (!found) return null;

  // Reconstruct path
  const path = [];
  let cx = endX, cy = endY;
  while (cx !== startX || cy !== startY) {
    path.unshift({ x: cx, y: cy });
    const idx = cy * MAP_SIZE + cx;
    const px = parent[idx * 2];
    const py = parent[idx * 2 + 1];
    cx = px;
    cy = py;
  }
  return path;
}

// Get station at position
function getStationAt(stationMap, x, y) {
  const idx = y * MAP_SIZE + x;
  return stationMap[idx] > 0 ? stationMap[idx] - 1 : null;
}

// Process one game tick
export function gameTick(state) {
  if (state.paused) return state;

  const newState = { ...state };
  newState.dateTicks++;

  // Advance date (1 day per tick at normal speed)
  const date = new Date(newState.date);
  date.setDate(date.getDate() + 1);
  newState.date = date;

  // Monthly processing
  if (newState.dateTicks % 30 === 0) {
    // Calculate monthly finances
    let income = 0;
    let expenses = 0;

    // Vehicle maintenance
    for (const v of newState.vehicles) {
      const def = VEHICLE_DEFS[v.defId];
      expenses += def.maintenance;
    }

    // Loan interest
    if (newState.loan > 0) {
      const interest = Math.floor(newState.loan * INTEREST_RATE / 12);
      expenses += interest;
    }

    // Passenger & cargo generation
    for (const town of newState.towns) {
      // Generate passengers
      const numPassengers = Math.floor(town.population / 20);
      for (let i = 0; i < numPassengers; i++) {
        // Pick a random destination town
        const destTown = newState.towns[Math.floor(Math.random() * newState.towns.length)];
        if (destTown.id !== town.id) {
          town.passengers.push({
            source: town.id,
            destination: destTown.id,
            rating: 50,
            age: 0,
          });
        }
      }
      // Increase service rating slightly
      town.serviceRating = Math.min(100, town.serviceRating + 1);
    }

    // Industry production
    for (const ind of newState.industries) {
      const def = INDUSTRY_TYPES[ind.type];
      if (!ind.active) continue;

      // Check input cargo if needed
      if (def.consumes) {
        if (ind.needsCargo && ind.needsCargo[def.consumes] >= 10) {
          ind.needsCargo[def.consumes] -= 10;
          ind.storage = Math.min(ind.maxStorage, ind.storage + 10);
          if (def.produces) {
            ind.cargo[def.produces] = (ind.cargo[def.produces] || 0) + 10;
          }
        }
      } else if (def.produces) {
        // Raw producer
        ind.cargo[def.produces] = (ind.cargo[def.produces] || 0) + 5;
        ind.cargo[def.produces] = Math.min(ind.maxStorage, ind.cargo[def.produces]);
      }
    }

    // Age passengers (decrease rating)
    for (const town of newState.towns) {
      for (const p of town.passengers) {
        p.age++;
        p.rating = Math.max(0, p.rating - 2);
      }
      // Remove old passengers
      town.passengers = town.passengers.filter(p => p.age < 60);
    }

    // Process vehicle deliveries
    for (const v of newState.vehicles) {
      if (v.status === 'running') {
        // Check if vehicle delivered anything
        if (v.delivered) {
          for (const cargo of v.delivered) {
            const cargoDef = Object.values(CARGO_TYPES).find(c => c.name === cargo.type);
            if (cargoDef) {
              const dist = v.currentStation ? 10 : 0; // simplified distance
              const fare = cargoDef.value * cargo.amount * (10 + dist);
              income += fare;
            }
          }
          v.delivered = [];
        }
      }
    }

    newState.monthlyIncome = income;
    newState.monthlyExpenses = expenses;
    newState.money += income - expenses;
    newState.monthlyProfit = [...newState.monthlyProfit.slice(-23), income - expenses];

    // Town growth
    for (const town of newState.towns) {
      if (town.serviceRating > 60) {
        town.population = Math.min(2000, town.population + Math.floor(Math.random() * 10) + 1);
      } else if (town.serviceRating < 30) {
        town.population = Math.max(10, town.population - Math.floor(Math.random() * 5));
      }
    }
  }

  // Daily vehicle movement
  for (const v of newState.vehicles) {
    if (v.status === 'running' && v.route && v.route.length > 0) {
      // Move towards next waypoint
      const next = v.route[v.currentWaypoint];
      if (next) {
        const dx = Math.sign(next.x - v.x);
        const dy = Math.sign(next.y - v.y);

        if (dx !== 0 || dy !== 0) {
          // Move one step
          const def = VEHICLE_DEFS[v.defId];
          const speed = def.speed / 3600; // tiles per day (rough)
          if (Math.random() < speed) {
            v.x += dx;
            v.y += dy;
          }

          // Check if arrived at waypoint
          if (v.x === next.x && v.y === next.y) {
            // Pick up / drop off cargo at station
            processVehicleAtStation(newState, v);
            v.currentWaypoint++;
            if (v.currentWaypoint >= v.route.length) {
              v.currentWaypoint = 0; // loop route
            }
          }
        }
      }
    }
  }

  return newState;
}

function processVehicleAtStation(state, vehicle) {
  const def = VEHICLE_DEFS[vehicle.defId];
  const stationId = getStationAt(state.stationMap, vehicle.x, vehicle.y);

  if (stationId === null) return;

  // Find which station this belongs to (town or industry)
  const town = state.towns.find(t => {
    const dist = Math.abs(t.x - vehicle.x) + Math.abs(t.y - vehicle.y);
    return dist < 10;
  });

  const industry = state.industries.find(i => {
    const dist = Math.abs(i.x - vehicle.x) + Math.abs(i.y - vehicle.y);
    return dist < 10;
  });

  // Drop off cargo
  for (const cargo of (vehicle.cargo || [])) {
    const cargoDef = Object.values(CARGO_TYPES).find(c => c.name === cargo.type);
    if (!cargoDef) continue;

    if (cargo.type === 'PASSENGERS' && town) {
      // Check if this town is the destination
      const matchingPassengers = town.passengers.filter(p => p.destination === cargo.destId);
      const count = Math.min(cargo.amount, matchingPassengers.length);
      for (let i = 0; i < count; i++) {
        const idx = town.passengers.findIndex(p => p.destination === cargo.destId);
        if (idx >= 0) {
          const p = town.passengers[idx];
          vehicle.delivered.push({ type: 'PASSENGERS', amount: 1, rating: p.rating });
          town.passengers.splice(idx, 1);
          town.serviceRating = Math.min(100, town.serviceRating + 2);
        }
      }
      cargo.amount -= count;
    } else if (industry) {
      const indDef = INDUSTRY_TYPES[industry.type];
      if (indDef.consumes && cargo.type === indDef.consumes) {
        const amount = Math.min(cargo.amount, 20);
        industry.needsCargo[cargo.type] = (industry.needsCargo[cargo.type] || 0) + amount;
        vehicle.delivered.push({ type: cargo.type, amount, rating: 50 });
        cargo.amount -= amount;
      }
    }
  }

  // Pick up cargo
  const remainingCap = def.capacity - (vehicle.cargo || []).reduce((s, c) => s + c.amount, 0);

  if (town && remainingCap > 0) {
    // Pick up passengers heading to other towns
    for (const p of town.passengers) {
      if (remainingCap <= 0) break;
      if (p.destination !== town.id) {
        if (!vehicle.cargo) vehicle.cargo = [];
        const existing = vehicle.cargo.find(c => c.type === 'PASSENGERS' && c.destId === p.destination);
        if (existing) {
          existing.amount++;
        } else {
          vehicle.cargo.push({ type: 'PASSENGERS', amount: 1, destId: p.destination });
        }
        const idx = town.passengers.indexOf(p);
        if (idx >= 0) town.passengers.splice(idx, 1);
        remainingCap--;
      }
    }
  }

  if (industry && remainingCap > 0) {
    const indDef = INDUSTRY_TYPES[industry.type];
    if (indDef.produces && industry.cargo[indDef.produces] > 0) {
      const amount = Math.min(remainingCap, industry.cargo[indDef.produces], 20);
      if (amount > 0) {
        if (!vehicle.cargo) vehicle.cargo = [];
        const existing = vehicle.cargo.find(c => c.type === indDef.produces);
        if (existing) {
          existing.amount += amount;
        } else {
          vehicle.cargo.push({ type: indDef.produces, amount, destId: null });
        }
        industry.cargo[indDef.produces] -= amount;
      }
    }
  }
}

// Game reducer
export function gameReducer(state, action) {
  switch (action.type) {
    case ACTIONS.TICK: {
      const ticks = state.gameSpeed === GAME_SPEED.FASTEST ? 4 :
                    state.gameSpeed === GAME_SPEED.FAST ? 2 : 1;
      let s = state;
      for (let i = 0; i < ticks; i++) {
        s = gameTick(s);
      }
      return s;
    }

    case ACTIONS.BUILD: {
      const { x, y, tileType } = action.payload;
      if (x < 0 || x >= MAP_SIZE || y < 0 || y >= MAP_SIZE) return state;
      const idx = y * MAP_SIZE + x;

      // Check cost
      const cost = BUILD_COSTS[tileType] || 0;
      if (state.money < cost) return state;

      const surface = new Uint8Array(state.surface);
      const features = new Uint8Array(state.features);
      const stationMap = new Uint8Array(state.stationMap);
      let money = state.money;

      if (tileType === TILE.STATION) {
        // Build a station (multiple tiles)
        const stationId = state.towns.length + state.industries.length + state.stations?.length || 100;
        for (let dx = -3; dx <= 3; dx++) {
          const nx = x + dx;
          if (nx < 0 || nx >= MAP_SIZE) continue;
          const nIdx = y * MAP_SIZE + nx;
          surface[nIdx] = TILE.STATION;
          stationMap[nIdx] = stationId + 1;
          features[nIdx] = 0;
        }
        money -= cost;
      } else if (tileType === TILE.AIRPORT) {
        const airportId = state.airports.length + 200;
        for (let dy = -5; dy <= 5; dy++) {
          for (let dx = -5; dx <= 5; dx++) {
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || nx >= MAP_SIZE || ny < 0 || ny >= MAP_SIZE) continue;
            const nIdx = ny * MAP_SIZE + nx;
            surface[nIdx] = TILE.AIRPORT;
            stationMap[nIdx] = airportId + 1;
            features[nIdx] = 0;
          }
        }
        money -= cost;
        state.airports.push({ id: airportId, x, y });
      } else if (tileType === TILE.DOCK) {
        surface[idx] = TILE.DOCK;
        stationMap[idx] = state.docks.length + 300;
        features[idx] = 0;
        money -= cost;
      } else {
        surface[idx] = tileType;
        if (tileType === TILE.ROAD || tileType === TILE.RAIL) {
          features[idx] = 0; // clear trees
        }
        money -= cost;
      }

      return { ...state, surface, features, stationMap, money };
    }

    case ACTIONS.DEMOLISH: {
      const { x, y } = action.payload;
      if (x < 0 || x >= MAP_SIZE || y < 0 || y >= MAP_SIZE) return state;
      const idx = y * MAP_SIZE + x;

      const surface = new Uint8Array(state.surface);
      const stationMap = new Uint8Array(state.stationMap);
      surface[idx] = 0;
      stationMap[idx] = 0;

      const refund = Math.floor((BUILD_COSTS[surface[idx]] || 0) * 0.5);
      return { ...state, surface, stationMap, money: state.money + refund };
    }

    case ACTIONS.BUY_VEHICLE: {
      const { defId, startX, startY, route } = action.payload;
      const def = VEHICLE_DEFS[defId];
      if (state.money < def.cost) return state;

      const vehicle = {
        id: state.nextVehicleId++,
        defId,
        name: def.name,
        x: startX,
        y: startY,
        cargo: [],
        delivered: [],
        route,
        currentWaypoint: 0,
        status: 'running',
        reliability: 100,
      };

      return {
        ...state,
        vehicles: [...state.vehicles, vehicle],
        money: state.money - def.cost,
      };
    }

    case ACTIONS.SCRAP_VEHICLE: {
      const { vehicleId } = action.payload;
      const def = VEHICLE_DEFS[state.vehicles.find(v => v.id === vehicleId)?.defId];
      const scrapValue = def ? Math.floor(def.cost * 0.25) : 0;
      return {
        ...state,
        vehicles: state.vehicles.filter(v => v.id !== vehicleId),
        money: state.money + scrapValue,
      };
    }

    case ACTIONS.CHANGE_TOOL:
      return { ...state, selectedTool: action.payload };

    case ACTIONS.CHANGE_SPEED:
      return { ...state, gameSpeed: action.payload, paused: action.payload === GAME_SPEED.PAUSED };

    case ACTIONS.TOGGLE_PAUSE:
      return { ...state, paused: !state.paused, gameSpeed: state.paused ? GAME_SPEED.NORMAL : GAME_SPEED.PAUSED };

    case ACTIONS.MOVE_CAMERA: {
      const { dx, dy } = action.payload;
      const viewSize = 32;
      return {
        ...state,
        cameraX: Math.max(0, Math.min(MAP_SIZE - viewSize, state.cameraX + dx)),
        cameraY: Math.max(0, Math.min(MAP_SIZE - viewSize, state.cameraY + dy)),
      };
    }

    case ACTIONS.ZOOM:
      return {
        ...state,
        zoom: Math.max(1, Math.min(6, state.zoom + (action.payload > 0 ? 1 : -1))),
      };

    case ACTIONS.TAKE_LOAN: {
      const newLoan = Math.min(MAX_LOAN, state.loan + LOAN_STEP);
      return { ...state, loan: newLoan, money: state.money + LOAN_STEP };
    }

    case ACTIONS.REPAY_LOAN: {
      const newLoan = Math.max(0, state.loan - LOAN_STEP);
      const repaid = state.loan - newLoan;
      return { ...state, loan: newLoan, money: state.money - repaid };
    }

    case ACTIONS.SHOW_PANEL:
      return { ...state, showPanel: action.payload };

    case ACTIONS.HIDE_PANEL:
      return { ...state, showPanel: null };

    case ACTIONS.SELECT_VEHICLE:
      return { ...state, selectedVehicle: action.payload };

    case ACTIONS.LOAD_GAME:
      return action.payload || state;

    case ACTIONS.NEW_GAME: {
      const { seed, difficulty } = action.payload;
      return createNewGame(seed, difficulty);
    }

    default:
      return state;
  }
}

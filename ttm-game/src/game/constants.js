// ===== GAME CONSTANTS =====

export const MAP_SIZE = 1024;
export const TILE_SIZE = 8; // base tile size for rendering

export const START_YEAR = 1920;
export const END_YEAR = 2020;
export const GAME_DURATION_YEARS = END_YEAR - START_YEAR;

// Terrain types
export const TERRAIN = {
  GRASS: 0,
  WATER: 1,
  HILLS: 2,
  MOUNTAIN: 3,
  DESERT: 4,
  SNOW: 5,
  TUNDRA: 6,
};

export const TERRAIN_COLORS = {
  [TERRAIN.GRASS]: '#4a8c3f',
  [TERRAIN.WATER]: '#2e6b9e',
  [TERRAIN.HILLS]: '#5a9c4f',
  [TERRAIN.MOUNTAIN]: '#8a8a8a',
  [TERRAIN.DESERT]: '#c4a44a',
  [TERRAIN.SNOW]: '#e8e8f0',
  [TERRAIN.TUNDRA]: '#b8c8d8',
};

export const TERRAIN_NAMES = {
  [TERRAIN.GRASS]: 'Grassland',
  [TERRAIN.WATER]: 'Water',
  [TERRAIN.HILLS]: 'Hills',
  [TERRAIN.MOUNTAIN]: 'Mountain',
  [TERRAIN.DESERT]: 'Desert',
  [TERRAIN.SNOW]: 'Snow',
  [TERRAIN.TUNDRA]: 'Tundra',
};

// Surface types (what can be built on)
export const SURFACE = {
  NONE: 0,
  ROAD: 1,
  RAIL: 2,
  STATION_TRAIN: 3,
  STATION_BUS: 4,
  STATION_TRUCK: 5,
  AIRPORT: 6,
  DOCK: 7,
  ROAD_STATION: 8,
};

// Surface colors for rendering
export const SURFACE_COLORS = {
  [SURFACE.NONE]: null,
  [SURFACE.ROAD]: '#555555',
  [SURFACE.RAIL]: '#4a3728',
  [SURFACE.STATION_TRAIN]: '#8b4513',
  [SURFACE.STATION_BUS]: '#2e8b57',
  [SURFACE.STATION_TRUCK]: '#b8860b',
  [SURFACE.AIRPORT]: '#666666',
  [SURFACE.DOCK]: '#8b6914',
  [SURFACE.ROAD_STATION]: '#2e8b57',
};

// Industry types
export const INDUSTRY_TYPES = [
  { id: 0, name: 'Coal Mine', produces: 'Coal', color: '#333333', needsRoad: false },
  { id: 1, name: 'Iron Ore Mine', produces: 'Iron Ore', color: '#8b4513', needsRoad: false },
  { id: 2, name: 'Quarry', produces: 'Stone', color: '#888888', needsRoad: false },
  { id: 3, name: 'Lumber Mill', produces: 'Wood', color: '#228b22', needsRoad: false },
  { id: 4, name: 'Farm', produces: 'Food', color: '#9acd32', needsRoad: false },
  { id: 5, name: 'Oil Well', produces: 'Oil', color: '#1a1a1a', needsRoad: false },
  { id: 6, name: 'Steelworks', produces: 'Steel', consumes: 'Iron Ore', color: '#b22222', needsRoad: true },
  { id: 7, name: 'Paper Mill', produces: 'Paper', consumes: 'Wood', color: '#f5f5dc', needsRoad: true },
  { id: 8, name: 'Bakery', produces: 'Baked Goods', consumes: 'Food', color: '#daa520', needsRoad: true },
  { id: 9, name: 'Car Factory', produces: 'Cars', consumes: 'Steel', color: '#4169e1', needsRoad: true },
  { id: 10, name: 'Refinery', produces: 'Fuel', consumes: 'Oil', color: '#dc143c', needsRoad: true },
  { id: 11, name: 'Spaceport', produces: 'Satellite', consumes: 'Cars', color: '#9370db', needsRoad: true },
];

// Cargo types
export const CARGO_TYPES = [
  { id: 0, name: 'Passengers', color: '#00ff00', value: 1 },
  { id: 1, name: 'Mail', color: '#ffff00', value: 2 },
  { id: 2, name: 'Coal', color: '#333333', value: 3 },
  { id: 3, name: 'Iron Ore', color: '#8b4513', value: 3 },
  { id: 4, name: 'Stone', color: '#888888', value: 2 },
  { id: 5, name: 'Wood', color: '#228b22', value: 3 },
  { id: 6, name: 'Food', color: '#9acd32', value: 3 },
  { id: 7, name: 'Oil', color: '#1a1a1a', value: 4 },
  { id: 8, name: 'Steel', color: '#b22222', value: 5 },
  { id: 9, name: 'Paper', color: '#f5f5dc', value: 4 },
  { id: 10, name: 'Baked Goods', color: '#daa520', value: 4 },
  { id: 11, name: 'Cars', color: '#4169e1', value: 6 },
  { id: 12, name: 'Fuel', color: '#dc143c', value: 5 },
  { id: 13, name: 'Satellite', color: '#9370db', value: 10 },
];

// Vehicle types
export const VEHICLE_CLASS = {
  RAIL: 'rail',
  ROAD: 'road',
  AIR: 'air',
  WATER: 'water',
};

// Vehicle definitions
export const VEHICLES = [
  // Trains
  { id: 0, name: 'Steam Locomotive', class: VEHICLE_CLASS.RAIL, type: 'engine', speed: 60, power: 200, cost: 8000, capacity: 0, reliability: 80, year: 1920, color: '#8b4513', length: 1 },
  { id: 1, name: 'Diesel Locomotive', class: VEHICLE_CLASS.RAIL, type: 'engine', speed: 100, power: 350, cost: 25000, capacity: 0, reliability: 90, year: 1935, color: '#228b22', length: 1 },
  { id: 2, name: 'Electric Locomotive', class: VEHICLE_CLASS.RAIL, type: 'engine', speed: 140, power: 500, cost: 60000, capacity: 0, reliability: 95, year: 1950, color: '#4169e1', length: 1 },
  { id: 3, name: 'High Speed Train', class: VEHICLE_CLASS.RAIL, type: 'engine', speed: 220, power: 800, cost: 150000, capacity: 0, reliability: 98, year: 1965, color: '#dc143c', length: 1 },
  { id: 4, name: 'Passenger Car', class: VEHICLE_CLASS.RAIL, type: 'wagon', speed: 0, power: 0, cost: 4000, capacity: 32, cargo: [0], reliability: 85, year: 1920, color: '#228b22', length: 1 },
  { id: 5, name: 'Cargo Wagon', class: VEHICLE_CLASS.RAIL, type: 'wagon', speed: 0, power: 0, cost: 3000, capacity: 20, cargo: [2,3,4,5,6,7,8,9,10,11,12,13], reliability: 85, year: 1920, color: '#8b4513', length: 1 },
  { id: 6, name: 'Mail Car', class: VEHICLE_CLASS.RAIL, type: 'wagon', speed: 0, power: 0, cost: 3500, capacity: 15, cargo: [1], reliability: 85, year: 1920, color: '#ffff00', length: 1 },

  // Road vehicles
  { id: 7, name: 'Minibus', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 50, power: 0, cost: 2000, capacity: 12, cargo: [0], reliability: 75, year: 1920, color: '#ff6347', length: 1 },
  { id: 8, name: 'Bus', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 65, power: 0, cost: 5000, capacity: 28, cargo: [0], reliability: 80, year: 1930, color: '#228b22', length: 1 },
  { id: 9, name: 'Coach', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 80, power: 0, cost: 12000, capacity: 60, cargo: [0], reliability: 85, year: 1945, color: '#4169e1', length: 1 },
  { id: 10, name: 'Cargo Truck', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 55, power: 0, cost: 4000, capacity: 10, cargo: [2,3,4,5,6,7,8,9,10,11,12], reliability: 75, year: 1920, color: '#8b4513', length: 1 },
  { id: 11, name: 'Long Distance Truck', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 70, power: 0, cost: 8000, capacity: 16, cargo: [2,3,4,5,6,7,8,9,10,11,12], reliability: 80, year: 1940, color: '#b8860b', length: 1 },
  { id: 12, name: 'Mail Van', class: VEHICLE_CLASS.ROAD, type: 'single', speed: 55, power: 0, cost: 3000, capacity: 8, cargo: [1], reliability: 75, year: 1920, color: '#ffff00', length: 1 },

  // Aircraft
  { id: 13, name: 'Cessna', class: VEHICLE_CLASS.AIR, type: 'single', speed: 200, power: 0, cost: 15000, capacity: 8, cargo: [0], reliability: 85, year: 1935, color: '#ffffff', length: 1 },
  { id: 14, name: 'DC-3', class: VEHICLE_CLASS.AIR, type: 'single', speed: 250, power: 0, cost: 45000, capacity: 24, cargo: [0], reliability: 90, year: 1940, color: '#c0c0c0', length: 1 },
  { id: 15, name: 'Boeing 707', class: VEHICLE_CLASS.AIR, type: 'single', speed: 500, power: 0, cost: 180000, capacity: 160, cargo: [0], reliability: 95, year: 1958, color: '#4169e1', length: 1 },
  { id: 16, name: 'Cargo Plane', class: VEHICLE_CLASS.AIR, type: 'single', speed: 350, power: 0, cost: 120000, capacity: 60, cargo: [2,3,4,5,6,8,9,10,11,12,13], reliability: 90, year: 1950, color: '#8b4513', length: 1 },
  { id: 17, name: 'Air Mail', class: VEHICLE_CLASS.AIR, type: 'single', speed: 250, power: 0, cost: 40000, capacity: 20, cargo: [1], reliability: 90, year: 1940, color: '#ffff00', length: 1 },

  // Ships
  { id: 18, name: 'Cargo Ship', class: VEHICLE_CLASS.WATER, type: 'single', speed: 30, power: 0, cost: 25000, capacity: 80, cargo: [2,3,4,5,6,7,8,9,10,11,12], reliability: 85, year: 1920, color: '#8b4513', length: 1 },
  { id: 19, name: 'Passenger Ship', class: VEHICLE_CLASS.WATER, type: 'single', speed: 35, power: 0, cost: 40000, capacity: 200, cargo: [0], reliability: 85, year: 1920, color: '#228b22', length: 1 },
  { id: 20, name: 'Ferry', class: VEHICLE_CLASS.WATER, type: 'single', speed: 40, power: 0, cost: 60000, capacity: 120, cargo: [0], reliability: 90, year: 1935, color: '#4169e1', length: 1 },
];

// Construction tools
export const TOOL = {
  CURSOR: 0,
  DEMOLISH: 1,
  BUILD_ROAD: 2,
  BUILD_RAIL: 3,
  BUILD_TRAIN_STATION: 4,
  BUILD_BUS_STOP: 5,
  BUILD_TRUCK_STOP: 6,
  BUILD_AIRPORT: 7,
  BUILD_DOCK: 8,
  BUILD_BRIDGE: 9,
  BUILD_TUNNEL: 10,
  TERRAIN_LOWER: 11,
  TERRAIN_RAISE: 12,
  FILL_WATER: 13,
  CREATE_WATER: 14,
  PLANT_TREES: 15,
  SIGNAL: 16,
};

export const TOOL_NAMES = {
  [TOOL.CURSOR]: 'Select',
  [TOOL.DEMOLISH]: 'Demolish',
  [TOOL.BUILD_ROAD]: 'Build Road',
  [TOOL.BUILD_RAIL]: 'Build Rail',
  [TOOL.BUILD_TRAIN_STATION]: 'Train Station',
  [TOOL.BUILD_BUS_STOP]: 'Bus Stop',
  [TOOL.BUILD_TRUCK_STOP]: 'Truck Stop',
  [TOOL.BUILD_AIRPORT]: 'Airport',
  [TOOL.BUILD_DOCK]: 'Dock',
  [TOOL.BUILD_BRIDGE]: 'Bridge',
  [TOOL.BUILD_TUNNEL]: 'Tunnel',
  [TOOL.TERRAIN_LOWER]: 'Lower Land',
  [TOOL.TERRAIN_RAISE]: 'Raise Land',
  [TOOL.FILL_WATER]: 'Fill Water',
  [TOOL.CREATE_WATER]: 'Create Water',
  [TOOL.PLANT_TREES]: 'Plant Trees',
  [TOOL.SIGNAL]: 'Signal',
};

export const TOOL_COSTS = {
  [TOOL.DEMOLISH]: 100,
  [TOOL.BUILD_ROAD]: 50,
  [TOOL.BUILD_RAIL]: 150,
  [TOOL.BUILD_TRAIN_STATION]: 1500,
  [TOOL.BUILD_BUS_STOP]: 500,
  [TOOL.BUILD_TRUCK_STOP]: 500,
  [TOOL.BUILD_AIRPORT]: 50000,
  [TOOL.BUILD_DOCK]: 10000,
  [TOOL.BUILD_BRIDGE]: 200,
  [TOOL.BUILD_TUNNEL]: 300,
  [TOOL.TERRAIN_LOWER]: 200,
  [TOOL.TERRAIN_RAISE]: 200,
  [TOOL.FILL_WATER]: 300,
  [TOOL.CREATE_WATER]: 300,
  [TOOL.PLANT_TREES]: 5,
  [TOOL.SIGNAL]: 100,
};

// Town growth stages
export const TOWN_STAGES = [
  { name: 'Hamlet', population: 50, color: '#9acd32' },
  { name: 'Village', population: 100, color: '#32cd32' },
  { name: 'Town', population: 250, color: '#228b22' },
  { name: 'City', population: 500, color: '#006400' },
  { name: 'Metropolis', population: 1000, color: '#004d00' },
];

// Difficulty settings
export const DIFFICULTY = {
  EASY: { startingMoney: 200000, maxLoan: 4000000, interestRate: 3, targetWealth: 2000000, constructionCost: 0.8, vehicleCost: 0.8, competition: false },
  NORMAL: { startingMoney: 100000, maxLoan: 4000000, interestRate: 5, targetWealth: 4000000, constructionCost: 1.0, vehicleCost: 1.0, competition: true },
  HARD: { startingMoney: 50000, maxLoan: 2000000, interestRate: 8, targetWealth: 8000000, constructionCost: 1.5, vehicleCost: 1.5, competition: true },
};

// Game speed (ticks per second)
export const GAME_SPEED = {
  PAUSED: 0,
  NORMAL: 1,
  FAST: 3,
  FASTEST: 6,
};

export const GAME_SPEED_NAMES = {
  [GAME_SPEED.PAUSED]: '⏸ Paused',
  [GAME_SPEED.NORMAL]: '▶ Normal',
  [GAME_SPEED.FAST]: '⏩ Fast',
  [GAME_SPEED.FASTEST]: '⏭ Fastest',
};

// Months
export const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Fare calculation
export const FARE_PER_TILE = 1.5; // base fare per tile distance

// Simulation tick rate (1 tick = 1 day)
export const TICKS_PER_DAY = 1;
export const DAYS_PER_MONTH = 30;
export const MONTHS_PER_YEAR = 12;

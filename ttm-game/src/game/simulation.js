// ===== GAME SIMULATION =====
// Handles one game tick (one day)

import {
  MAP_SIZE, TERRAIN, TILE, CARGO_TYPES, VEHICLE_DEFS,
  VEHICLE_CLASSES, VEHICLE_CLASS_SURFACE, TOWN_SIZES,
  FARE_PER_TILE, DAYS_PER_MONTH, MONTH_NAMES
} from './constants.js';
import { findPath, getStationAtPos, getStation, buildStation } from './state.js';

// ---- Main tick ----

export function gameTick(state) {
  if (state.paused) return state;

  let newState = { ...state };
  newState.dateTicks++;

  // Advance date
  const date = new Date(newState.date);
  date.setDate(date.getDate() + 1);
  newState.date = date;

  // ---- Vehicle simulation ----
  newState = simulateVehicles(newState);

  // ---- Monthly processing (every 30 days) ----
  if (newState.dateTicks % DAYS_PER_MONTH === 0) {
    newState = monthlyProcessing(newState);
  }

  // ---- Passenger generation (every few days) ----
  if (newState.dateTicks % 3 === 0) {
    newState = generatePassengers(newState);
  }

  // ---- Industry production (every 5 days) ----
  if (newState.dateTicks % 5 === 0) {
    newState = industryProduction(newState);
  }

  // ---- Town growth (every 30 days, in monthly processing) ----

  return newState;
}

// ---- Vehicle Simulation ----

function simulateVehicles(state) {
  const newVehicles = state.vehicles.map(vehicle => {
    if (vehicle.brokenDown) {
      // Try to repair
      vehicle.breakdownTimer--;
      if (vehicle.breakdownTimer <= 0) {
        return { ...vehicle, brokenDown: false, state: 'idle' };
      }
      return vehicle;
    }

    // Check for breakdown
    const def = VEHICLE_DEFS[vehicle.defId];
    if (Math.random() * 100 < (100 - def.reliability) / 365) {
      return { ...vehicle, brokenDown: true, breakdownTimer: 30 + Math.floor(Math.random() * 60) };
    }

    // If idle, find cargo
    if (vehicle.state === 'idle') {
      return tryLoadCargo(state, vehicle);
    }

    // If loading/unloading
    if (vehicle.state === 'loading' || vehicle.state === 'unloading') {
      const station = getStation(state, vehicle.stationId);
      if (!station) return { ...vehicle, state: 'idle' };

      if (vehicle.state === 'loading') {
        // Load cargo from station
        const loaded = loadFromStation(state, station, vehicle);
        return { ...loaded.vehicle, state: hasCargo(loaded.vehicle) ? 'moving' : 'idle' };
      } else {
        // Unload cargo
        const nextStationId = getNextStationInRoute(state, vehicle);
        if (nextStationId === null) {
          // End of route, unload and idle
          const unloaded = unloadAtStation(state, vehicle);
          return { ...unloaded.vehicle, state: 'idle', stationId: vehicle.stationId };
        }
        // Unload and move to next
        const unloaded = unloadAtStation(state, vehicle);
        return { ...unloaded.vehicle, state: 'moving', stationId: nextStationId };
      }
    }

    // Moving - advance towards target
    return moveVehicle(state, vehicle);
  });

  return { ...state, vehicles: newVehicles };
}

function hasCargo(vehicle) {
  return vehicle.cargo.length > 0;
}

function tryLoadCargo(state, vehicle) {
  const def = VEHICLE_DEFS[vehicle.defId];
  const station = getStation(state, vehicle.stationId);
  if (!station) return vehicle;

  // Check if there's cargo we can carry at this station
  // For passengers
  if (def.cargoTypes.includes(0) && station.waitingPassengers > 0) {
    return { ...vehicle, state: 'loading', stationId: station.id };
  }
  // For mail
  if (def.cargoTypes.includes(1) && station.waitingMail > 0) {
    return { ...vehicle, state: 'loading', stationId: station.id };
  }
  // For goods
  for (const cargoId of def.cargoTypes) {
    if (cargoId <= 0) continue; // skip passengers/mail (handled above)
    if (station.waitingCargo[cargoId] && station.waitingCargo[cargoId] > 0) {
      return { ...vehicle, state: 'loading', stationId: station.id };
    }
  }

  // If vehicle has a route, move to next station
  if (vehicle.route.length > 0) {
    const nextStationId = getNextStationInRoute(state, vehicle);
    if (nextStationId !== null) {
      return { ...vehicle, state: 'moving', stationId: nextStationId };
    }
  }

  return vehicle;
}

function getNextStationInRoute(state, vehicle) {
  if (vehicle.route.length === 0) return null;
  const nextIdx = vehicle.routeIndex + 1;
  if (nextIdx >= vehicle.route.length) return null;
  return vehicle.route[nextIdx];
}

function loadFromStation(state, station, vehicle) {
  const def = VEHICLE_DEFS[vehicle.defId];
  let remainingCapacity = def.capacity;
  let newCargo = vehicle.cargo.map(c => ({ ...c }));
  let stationCopy = { ...station };
  let loadedSomething = false;

  // Load passengers
  if (def.cargoTypes.includes(0) && station.waitingPassengers > 0) {
    const count = Math.min(station.waitingPassengers, remainingCapacity);
    const existing = newCargo.find(c => c.type === 0);
    if (existing) {
      existing.amount += count;
    } else {
      newCargo.push({ type: 0, amount: count, source: station.id });
    }
    stationCopy.waitingPassengers -= count;
    remainingCapacity -= count;
    loadedSomething = true;
  }

  // Load mail
  if (def.cargoTypes.includes(1) && station.waitingMail > 0) {
    const count = Math.min(station.waitingMail, remainingCapacity);
    const existing = newCargo.find(c => c.type === 1);
    if (existing) existing.amount += count;
    else newCargo.push({ type: 1, amount: count, source: station.id });
    stationCopy.waitingMail -= count;
    remainingCapacity -= count;
    loadedSomething = true;
  }

  // Load goods
  for (const cargoId of def.cargoTypes) {
    if (cargoId <= 1 || remainingCapacity <= 0) continue;
    if (stationCopy.waitingCargo[cargoId] && stationCopy.waitingCargo[cargoId] > 0) {
      const count = Math.min(stationCopy.waitingCargo[cargoId], remainingCapacity);
      const existing = newCargo.find(c => c.type === cargoId);
      if (existing) existing.amount += count;
      else newCargo.push({ type: cargoId, amount: count, source: station.id });
      stationCopy.waitingCargo[cargoId] -= count;
      remainingCapacity -= count;
      loadedSomething = true;
    }
  }

  // Update station in state
  const stations = state.stations.map(s => s.id === station.id ? stationCopy : s);

  return {
    vehicle: { ...vehicle, cargo: newCargo },
    state: { ...state, stations },
    loadedSomething,
  };
}

function unloadAtStation(state, vehicle) {
  const def = VEHICLE_DEFS[vehicle.defId];
  const destStation = getStation(state, vehicle.stationId);
  if (!destStation) return { vehicle, state };

  let income = 0;
  const newCargo = [];

  for (const cargo of vehicle.cargo) {
    const cargoDef = CARGO_TYPES[cargo.type];
    if (!cargoDef) continue;

    // Calculate distance for fare
    const sourceStation = getStation(state, cargo.source);
    let distance = 1;
    if (sourceStation && destStation) {
      distance = Math.max(1, Math.hypot(sourceStation.x - destStation.x, sourceStation.y - destStation.y));
    }

    const fare = Math.floor(cargoDef.value * distance * FARE_PER_TILE);
    income += fare * cargo.amount;

    // Deliver passengers to towns
    if (cargo.type === 0) {
      // Passengers go to nearest town
      for (const town of state.towns) {
        if (Math.hypot(town.x - destStation.x, town.y - destStation.y) < 20) {
          town.serviceRating = Math.min(100, town.serviceRating + 1);
        }
      }
    }

    // Deliver goods to industries
    if (cargo.type > 1) {
      for (const ind of state.industries) {
        if (ind.consumesCargoId === cargo.type && Math.hypot(ind.x - destStation.x, ind.y - destStation.y) < 20) {
          ind.connected = true;
        }
      }
    }

    // Keep excess cargo
    // (In a full game, we'd track which cargo needs to go where)
  }

  // Add income to state
  const newState = { ...state, money: state.money + income };
  if (income > 0) {
    newState.notifications = [...state.notifications, `+$${income} from ${def.name}`];
  }

  return { vehicle: { ...vehicle, cargo: newCargo }, state: newState };
}

function moveVehicle(state, vehicle) {
  const def = VEHICLE_DEFS[vehicle.defId];
  const targetStation = getStation(state, vehicle.stationId);
  if (!targetStation) return { ...vehicle, state: 'idle' };

  // Already at target
  if (vehicle.x === targetStation.x && vehicle.y === targetStation.y) {
    // If we had cargo, unload; if we have a route, find next station
    if (hasCargo(vehicle)) {
      return { ...vehicle, state: 'unloading' };
    }
    // Move to next station in route
    if (vehicle.route.length > 0) {
      const nextIdx = vehicle.routeIndex + 1;
      if (nextIdx < vehicle.route.length) {
        return { ...vehicle, routeIndex: nextIdx, state: 'loading' };
      }
    }
    return { ...vehicle, state: 'idle' };
  }

  // Find path to target
  const requiredSurface = VEHICLE_CLASS_SURFACE[def.cls];
  const path = findPath(state.surface, state.terrain, vehicle.x, vehicle.y,
    targetStation.x, targetStation.y, requiredSurface, 2000);

  if (!path || path.length === 0) {
    // Can't reach target, go idle
    return { ...vehicle, state: 'idle' };
  }

  // Move one step along path (speed affects how fast)
  const speedFactor = def.speed / 100;
  const step = Math.max(1, Math.floor(speedFactor));

  const nextPos = path[Math.min(step, path.length - 1)];
  return { ...vehicle, x: nextPos.x, y: nextPos.y, tileProgress: 0 };
}

// ---- Monthly Processing ----

function monthlyProcessing(state) {
  let newState = { ...state };
  let income = 0;
  let expenses = 0;

  // Vehicle maintenance
  for (const v of newState.vehicles) {
    const def = VEHICLE_DEFS[v.defId];
    expenses += def.maintenance;
  }

  // Loan interest
  if (newState.loan > 0) {
    const interest = Math.floor(newState.loan * newState.interestRate / 12);
    expenses += interest;
  }

  // Town growth
  const newTowns = newState.towns.map(town => {
    let newTown = { ...town };
    // Grow if service rating is good
    if (newTown.serviceRating > 40) {
      newTown.population += Math.floor(newTown.serviceRating / 10);
      newTown.growthTimer++;
    } else {
      newTown.population = Math.max(10, newTown.population - 2);
    }
    // Cap population
    newTown.population = Math.min(2000, newTown.population);
    // Decay service rating
    newTown.serviceRating = Math.max(0, newTown.serviceRating - 2);
    return newTown;
  });
  newState.towns = newTowns;

  // Calculate profit
  const profit = income - expenses;
  newState.money += profit;
  newState.monthlyIncome = income;
  newState.monthlyExpenses = expenses;
  newState.monthlyProfit = [...newState.monthlyProfit.slice(-23), profit];

  // Auto-save every 5 months
  if (newState.dateTicks % (DAYS_PER_MONTH * 5) === 0) {
    // Auto-save handled by the UI layer
  }

  return newState;
}

// ---- Passenger Generation ----

function generatePassengers(state) {
  const newTowns = state.towns.map(town => {
    const newTown = { ...town };
    const numPassengers = Math.max(1, Math.floor(town.population / 30));

    for (let i = 0; i < numPassengers; i++) {
      if (newTown.passengersWaiting >= 50) break;
      // Pick random destination
      const destIdx = Math.floor(Math.random() * state.towns.length);
      if (destIdx === town.id) continue;

      newTown.passengersWaiting++;
    }

    // Mail
    if (Math.random() < 0.3) {
      newTown.mailWaiting = Math.min(20, newTown.mailWaiting + 1);
    }

    return newTown;
  });

  // Assign waiting passengers to nearest station
  const stations = state.stations.map(station => {
    let newStation = { ...station };
    for (const town of newTowns) {
      if (Math.hypot(town.x - station.x, town.y - station.y) < 25) {
        newStation.waitingPassengers += Math.floor(town.passengersWaiting / Math.max(1, newTowns.length));
        newStation.waitingMail += Math.floor(town.mailWaiting / Math.max(1, newTowns.length));
      }
    }
    return newStation;
  });

  // Reset town waiting counts
  const resetTowns = newTowns.map(t => ({ ...t, passengersWaiting: 0, mailWaiting: 0 }));

  return { ...state, towns: resetTowns, stations };
}

// ---- Industry Production ----

function industryProduction(state) {
  const newIndustries = state.industries.map(industry => {
    const newInd = { ...industry };

    if (!newInd.active) return newInd;

    // Check if it needs input cargo
    if (newInd.consumesCargoId !== null) {
      // Check if we have the needed cargo
      const hasInput = false; // simplified - in full game check connections
      if (!hasInput && !newInd.connected) return newInd;
    }

    // Produce output
    if (newInd.storage < newInd.maxStorage) {
      newInd.storage = Math.min(newInd.maxStorage, newInd.storage + newInd.productionRate);
    }

    // Add cargo to nearest station
    if (newInd.storage > 0) {
      const stations = state.stations.map(station => {
        if (Math.hypot(station.x - newInd.x, station.y - newInd.y) < 25) {
          const newStation = { ...station };
          if (!newStation.waitingCargo[newInd.producesCargoId]) {
            newStation.waitingCargo[newInd.producesCargoId] = 0;
          }
          const transfer = Math.min(newInd.storage, 10);
          newStation.waitingCargo[newInd.producesCargoId] += transfer;
          return newStation;
        }
        return station;
      });

      newInd.storage -= Math.min(newInd.storage, 10);
      return { ...newInd, stations };
    }

    return newInd;
  });

  // Collect station updates from industries
  // (simplified - in real impl, stations would be updated properly)
  return { ...state, industries: newIndustries };
}

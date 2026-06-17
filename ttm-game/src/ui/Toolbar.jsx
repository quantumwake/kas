// ===== TOOLBAR =====

import React from 'react';
import { TOOLS, TOOL_NAMES, TOOL_ICONS, BUILD_COSTS } from '../game/constants.js';
import { ACTIONS } from '../game/state.js';

// Group tools for the toolbar
const TOOL_GROUPS = [
  { name: 'Tools', tools: [TOOLS.CURSOR, TOOLS.DEMOLISH] },
  { name: 'Build', tools: [TOOLS.BUILD_ROAD, TOOLS.BUILD_RAIL, TOOLS.SIGNAL, TOOLS.BUILD_BRIDGE] },
  { name: 'Stations', tools: [TOOLS.BUILD_STATION, TOOLS.BUILD_BUS_STOP, TOOLS.BUILD_TRUCK_STOP, TOOLS.BUILD_AIRPORT, TOOLS.BUILD_DOCK] },
  { name: 'Terrain', tools: [TOOLS.TERRAIN_LOWER, TOOLS.TERRAIN_RAISE, TOOLS.FILL_WATER, TOOLS.CREATE_WATER, TOOLS.PLANT_TREES] },
];

export default function Toolbar({ state, dispatch }) {
  return (
    <div className="toolbar">
      {TOOL_GROUPS.map((group, gi) => (
        <React.Fragment key={group.name}>
          {gi > 0 && <div className="tool-separator" />}
          {group.tools.map((tool) => (
            <button
              key={tool}
              className={`tool-btn ${state.selectedTool === tool ? 'active' : ''}`}
              onClick={() => dispatch({ type: ACTIONS.CHANGE_TOOL, payload: tool })}
              title={`${TOOL_NAMES[tool]}${BUILD_COSTS[tool] ? ` ($${BUILD_COSTS[tool]})` : ''}`}
            >
              <span className="icon">{TOOL_ICONS[tool]}</span>
              <span>{TOOL_NAMES[tool]}</span>
              {BUILD_COSTS[tool] && <span className="cost">${BUILD_COSTS[tool]}</span>}
            </button>
          ))}
        </React.Fragment>
      ))}

      <div className="tool-separator" />

      {/* Vehicle button */}
      <button
        className="tool-btn"
        onClick={() => dispatch({ type: ACTIONS.SHOW_PANEL, payload: 'vehicle' })}
      >
        <span className="icon">🚂</span>
        <span>Vehicles</span>
      </button>

      {/* Economy button */}
      <button
        className="tool-btn"
        onClick={() => dispatch({ type: ACTIONS.SHOW_PANEL, payload: 'economy' })}
      >
        <span className="icon">📊</span>
        <span>Economy</span>
      </button>

      {/* Save/Load button */}
      <button
        className="tool-btn"
        onClick={() => dispatch({ type: ACTIONS.SHOW_PANEL, payload: 'saveload' })}
      >
        <span className="icon">💾</span>
        <span>Save</span>
      </button>
    </div>
  );
}

// ===== ECONOMY PANEL =====

import React from 'react';
import { ACTIONS } from '../game/state.js';

export default function EconomyPanel({ state, dispatch, onClose }) {
  const profit = state.monthlyProfit;
  const lastProfit = profit.length > 0 ? profit[profit.length - 1] : 0;
  const totalVehicles = state.vehicles.length;
  const totalStations = state.stations.length + state.docks.length + state.airports.length;
  const totalTowns = state.towns.length;
  const totalIndustries = state.industries.length;

  // Simple bar chart for monthly profit
  const maxProfit = Math.max(1, ...profit.map(Math.abs));

  return (
    <div className="panel" style={{ minWidth: '500px' }}>
      <button className="panel-close" onClick={onClose}>✕</button>
      <h2>📊 Economy</h2>

      <div className="grid-3" style={{ marginBottom: '16px' }}>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Money</span>
          <span className={`value ${state.money >= 0 ? 'money-positive' : 'money-negative'}`}>
            ${state.money.toLocaleString()}
          </span>
        </div>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Loan</span>
          <span className="value">${state.loan.toLocaleString()}</span>
        </div>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Net Worth</span>
          <span className="value">${(state.money + state.loan * -1).toLocaleString()}</span>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '16px' }}>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Income/mo</span>
          <span className="money-positive value">${state.monthlyIncome.toLocaleString()}</span>
        </div>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Expenses/mo</span>
          <span className="money-negative value">${state.monthlyExpenses.toLocaleString()}</span>
        </div>
        <div className="hud-stat" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="label">Profit/mo</span>
          <span className={`${lastProfit >= 0 ? 'money-positive' : 'money-negative'} value`}>
            ${lastProfit.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Profit chart */}
      <div style={{ marginBottom: '16px' }}>
        <div className="label" style={{ marginBottom: '6px' }}>Monthly Profit (last 12 months)</div>
        <div style={{ height: '100px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', display: 'flex', alignItems: 'flex-end', padding: '4px', gap: '2px' }}>
          {profit.slice(-12).map((p, i) => {
            const height = Math.max(2, (Math.abs(p) / maxProfit) * 90);
            return (
              <div key={i} style={{
                flex: 1,
                height: `${height}px`,
                background: p >= 0 ? '#2ecc71' : '#e74c3c',
                borderRadius: '2px 2px 0 0',
                minWidth: '8px',
              }} title={`$${p.toLocaleString()}`} />
            );
          })}
          {profit.slice(-12).length === 0 && (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid-2" style={{ marginBottom: '16px' }}>
        <div><span className="label">Vehicles:</span> <strong>{totalVehicles}</strong></div>
        <div><span className="label">Stations:</span> <strong>{totalStations}</strong></div>
        <div><span className="label">Towns:</span> <strong>{totalTowns}</strong></div>
        <div><span className="label">Industries:</span> <strong>{totalIndustries}</strong></div>
      </div>

      {/* Loan controls */}
      <div style={{ borderTop: '1px solid #2a4a6b', paddingTop: '12px' }}>
        <div className="label" style={{ marginBottom: '8px' }}>Bank Loans</div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-success" onClick={() => dispatch({ type: ACTIONS.TAKE_LOAN })}>
            Borrow $10,000
          </button>
          <button className="btn btn-danger" onClick={() => dispatch({ type: ACTIONS.REPAY_LOAN })}>
            Repay $10,000
          </button>
        </div>
        <div style={{ marginTop: '6px', fontSize: '12px', color: '#888' }}>
          Interest: {(state.interestRate * 100).toFixed(0)}%/year | Max loan: ${state.maxLoan.toLocaleString()}
        </div>
      </div>

      {/* Target */}
      <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(74,122,170,0.2)', borderRadius: '4px' }}>
        <div className="label">Win Target</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ flex: 1, height: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${Math.min(100, (state.money / (state.targetWealth || 4000000)) * 100)}%`,
              background: state.money >= (state.targetWealth || 4000000) ? '#2ecc71' : '#4a7aaa',
              borderRadius: '6px',
              transition: 'width 0.3s',
            }} />
          </div>
          <span style={{ fontSize: '12px', color: '#888' }}>
            {((state.money / (state.targetWealth || 4000000)) * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}

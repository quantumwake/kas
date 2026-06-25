import React from 'react';
import KPICard from './components/KPICard';
import RevenueChart from './components/RevenueChart';
import UserGrowthChart from './components/UserGrowthChart';
import CategoryChart from './components/CategoryChart';
import { kpis } from './data';

const App = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Business Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Overview of key metrics and performance</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-8 py-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {kpis.map((kpi, index) => (
            <KPICard key={index} label={kpi.label} value={kpi.value} icon={kpi.icon} />
          ))}
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <RevenueChart />
          <UserGrowthChart />
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-1 max-w-2xl mx-auto">
          <CategoryChart />
        </div>
      </main>
    </div>
  );
};

export default App;

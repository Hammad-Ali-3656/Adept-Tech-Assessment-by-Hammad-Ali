import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import CustomerExplorerPage from './pages/CustomerExplorerPage';
import WhatIfPage from './pages/WhatIfPage';
import HypotheticalPage from './pages/HypotheticalPage';
import ModelAnalyticsPage from './pages/ModelAnalyticsPage';
import { fetchStats } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCustomerId, setSelectedCustomerId] = useState('7590-VHVEG');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats()
      .then((data) => setStats(data))
      .catch((err) => console.error('Error loading global stats:', err));
  }, []);

  const handleSelectCustomer = (id) => {
    setSelectedCustomerId(id);
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        stats={stats}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <DashboardPage
            onNavigateTab={setActiveTab}
            onSelectCustomer={handleSelectCustomer}
          />
        )}
        {activeTab === 'chat' && <ChatPage />}
        {activeTab === 'customers' && (
          <CustomerExplorerPage
            onNavigateTab={setActiveTab}
            onSelectCustomer={handleSelectCustomer}
          />
        )}
        {activeTab === 'whatif' && (
          <WhatIfPage selectedCustomerId={selectedCustomerId} />
        )}
        {activeTab === 'hypothetical' && <HypotheticalPage />}
        {activeTab === 'model' && <ModelAnalyticsPage />}
      </main>
    </div>
  );
}

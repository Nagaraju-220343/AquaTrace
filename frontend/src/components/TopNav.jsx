import React from 'react';
import { Activity, LayoutDashboard, BarChart2, Radio, Map } from 'lucide-react';
import './TopNav.css';

export default function TopNav({ activeTab, setActiveTab }) {
  return (
    <div className="topnav">
      <a href="#" className="brand">
        <div className="brand-icon">
          <Radio size={20} color="white" />
        </div>
        <div className="brand-name">AquaTrace</div>
      </a>

      <div className="nav-tabs">
        <div
          className={`nav-tab ${activeTab === 'analyze' ? 'active' : ''}`}
          onClick={() => setActiveTab('analyze')}
        >
          <Activity size={16} className="tab-icon" />
          Analyze
        </div>
        <div
          className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          <LayoutDashboard size={16} className="tab-icon" />
          Results
        </div>
        <div
          className={`nav-tab ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          <BarChart2 size={16} className="tab-icon" />
          Reports
        </div>
        <div
          className={`nav-tab ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')}
        >
          <Map size={16} className="tab-icon" />
          Map View
        </div>
      </div>

      <div className="nav-status">
        <div className="status-dot"></div>
        Backend Online
      </div>
    </div>
  );
}

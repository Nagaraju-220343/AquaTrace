import React, { useState, useEffect } from 'react';
import TopNav from './components/TopNav';
import AnalyzePage from './pages/AnalyzePage';
import ResultsPage from './pages/ResultsPage';
import ReportsPage from './pages/ReportsPage';
import MapPage from './pages/MapPage';
import './App.css';

function App() {
  const [activeTab, setActiveTab]     = useState('analyze');
  const [jobId, setJobId]             = useState(null);
  const [jobImageUrl, setJobImageUrl] = useState(null);

  useEffect(() => {
    const titles = { analyze: 'Analyze', results: 'Results', reports: 'Reports', map: 'Map View' };
    document.title = `${titles[activeTab] || 'Dashboard'} - BlueOrbit V1`;
  }, [activeTab]);

  return (
    <>
      <TopNav activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="app-body">
        <div className={`page ${activeTab === 'analyze' ? 'active' : ''}`}>
          <AnalyzePage
            setJobId={setJobId}
            setJobImageUrl={setJobImageUrl}
            setActiveTab={setActiveTab}
          />
        </div>
        <div className={`page ${activeTab === 'results' ? 'active' : ''}`}>
          <ResultsPage jobId={jobId} jobImageUrl={jobImageUrl} />
        </div>
        <div className={`page ${activeTab === 'reports' ? 'active' : ''}`}>
          <ReportsPage />
        </div>
        <div className={`page ${activeTab === 'map' ? 'active' : ''}`}>
          <MapPage />
        </div>
      </div>
    </>
  );
}

export default App;


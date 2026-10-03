import { useState } from 'react';
import Market from './pages/Market';
import PipelineHealth from './pages/PipelineHealth';
import './index.css';

type Tab = 'market' | 'health';

export default function App() {
  const [tab, setTab] = useState<Tab>('market');

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>UAE Property Listings</h1>
        <p>Property market analytics and pipeline monitoring</p>
      </header>

      <nav className="tab-bar">
        <button
          className={`tab-btn ${tab === 'market' ? 'active' : ''}`}
          onClick={() => setTab('market')}
        >
          Market
        </button>
        <button
          className={`tab-btn ${tab === 'health' ? 'active' : ''}`}
          onClick={() => setTab('health')}
        >
          Pipeline Health
        </button>
      </nav>

      {tab === 'market' ? <Market /> : <PipelineHealth />}
    </div>
  );
}

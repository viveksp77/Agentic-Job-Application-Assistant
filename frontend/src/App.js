import React, { useState } from 'react';
import HomePage from './pages/HomePage';
import HistoryPage from './pages/HistoryPage';
import InterviewPage from './pages/InterviewPage';
import './App.css';

export default function App() {
  const [page, setPage] = useState('home');

  return (
    <div className="app">
      <nav className="nav">
        <div className="nav-brand">
          <span className="nav-icon">⚡</span>
          <span className="nav-title">JobAgent AI</span>
        </div>
        <div className="nav-links">
          <button
            className={`nav-btn ${page === 'home' ? 'active' : ''}`}
            onClick={() => setPage('home')}
          >
            Analyse
          </button>
          <button
            className={`nav-btn ${page === 'interview' ? 'active' : ''}`}
            onClick={() => setPage('interview')}
          >
            Mock Interview
          </button>
          <button
            className={`nav-btn ${page === 'history' ? 'active' : ''}`}
            onClick={() => setPage('history')}
          >
            History
          </button>
        </div>
      </nav>

      <main className="main">
        {page === 'home' && <HomePage />}
        {page === 'interview' && <InterviewPage />}
        {page === 'history' && <HistoryPage />}
      </main>
    </div>
  );
}
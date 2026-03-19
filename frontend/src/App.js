import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import HomePage from './pages/HomePage';
import HistoryPage from './pages/HistoryPage';
import InterviewPage from './pages/InterviewPage';
import './App.css';

function AppContent() {
  const { user, logout, loading } = useAuth();
  const [page, setPage] = useState('home');

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', color: 'var(--muted)' }}>
        Loading...
      </div>
    );
  }

  if (!user) return <AuthPage />;

  return (
    <div className="app">
      <nav className="nav">
        <div className="nav-brand">
          <span className="nav-icon">⚡</span>
          <span className="nav-title">JobAgent AI</span>
        </div>

        <div className="nav-links">
          <button className={`nav-btn ${page === 'home' ? 'active' : ''}`}
            onClick={() => setPage('home')}>Analyse</button>
          <button className={`nav-btn ${page === 'interview' ? 'active' : ''}`}
            onClick={() => setPage('interview')}>Mock Interview</button>
          <button className={`nav-btn ${page === 'history' ? 'active' : ''}`}
            onClick={() => setPage('history')}>History</button>
        </div>

        {/* User menu */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: '0.85rem', color: 'var(--muted)',
            background: 'var(--bg3)', border: '1px solid var(--border2)',
            borderRadius: 99, padding: '4px 12px',
          }}>
            👤 {user.username}
          </span>
          <button className="nav-btn" onClick={logout}
            style={{ color: 'var(--danger)' }}>
            Sign out
          </button>
        </div>
      </nav>

      <main className="main">
        {page === 'home'      && <HomePage />}
        {page === 'interview' && <InterviewPage />}
        {page === 'history'   && <HistoryPage />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
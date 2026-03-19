import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import HomePage from './pages/HomePage';
import HistoryPage from './pages/HistoryPage';
import InterviewPage from './pages/InterviewPage';
import AuthPage from './pages/AuthPage';
import AnalyticsPage from './pages/AnalyticsPage';
import './App.css';

function NavBar() {
  const { user, logout } = useAuth();

  const navStyle = {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 32px', height: 56, background: '#0f0f1a',
    borderBottom: '1px solid #1e1e2e', position: 'sticky', top: 0, zIndex: 100,
  };

  const linkStyle = ({ isActive }) => ({
    color: isActive ? '#fff' : '#888', textDecoration: 'none',
    fontSize: 14, fontWeight: isActive ? 600 : 400,
    padding: '6px 14px', borderRadius: 8,
    background: isActive ? '#1e1e2e' : 'transparent', transition: 'all 0.15s',
  });

  return (
    <nav style={navStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color: '#f59e0b', fontSize: 20 }}>⚡</span>
        <span style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>JobAgent AI</span>
      </div>
      <div style={{ display: 'flex', gap: 4 }}>
        <NavLink to="/" end style={linkStyle}>Analyse</NavLink>
        <NavLink to="/interview" style={linkStyle}>Mock Interview</NavLink>
        <NavLink to="/history" style={linkStyle}>History</NavLink>
        <NavLink to="/analytics" style={linkStyle}>Analytics</NavLink>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {user && (
          <span style={{
            color: '#aaa', fontSize: 13, background: '#1e1e2e',
            padding: '4px 12px', borderRadius: 20,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            👤 {user.username}
          </span>
        )}
        <button onClick={logout} style={{
          background: 'none', border: 'none', color: '#f87171',
          cursor: 'pointer', fontSize: 14, fontWeight: 500,
        }}>
          Sign out
        </button>
      </div>
    </nav>
  );
}

function ProtectedRoutes() {
  const { user, loading: authLoading } = useAuth();

  // Lifted state — survives navigation between tabs
  const [analysisResults, setAnalysisResults] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  if (authLoading) return (
    <div style={{ color: '#aaa', textAlign: 'center', marginTop: 80 }}>Loading…</div>
  );
  if (!user) return <Navigate to="/auth" replace />;

  return (
    <>
      <NavBar />
      <Routes>
        <Route
          path="/"
          element={
            <HomePage
              persistedResults={analysisResults}
              setPersistedResults={setAnalysisResults}
              persistedLoading={analysisLoading}
              setPersistedLoading={setAnalysisLoading}
            />
          }
        />
        <Route path="/interview" element={<InterviewPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <div style={{ minHeight: '100vh', background: '#0f0f1a' }}>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/*" element={<ProtectedRoutes />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}
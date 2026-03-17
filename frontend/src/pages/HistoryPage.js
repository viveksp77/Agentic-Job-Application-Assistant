import React, { useEffect, useState } from 'react';
import { getHistory } from '../api/agent';

function getScoreClass(score) {
  if (score >= 85) return 'excellent';
  if (score >= 70) return 'good';
  if (score >= 50) return 'fair';
  return 'poor';
}

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getHistory()
      .then(data => setHistory(Array.isArray(data) ? data.reverse() : []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ color: 'var(--muted)', padding: '2rem' }}>Loading history...</div>;
  if (error) return <div className="error-msg">{error}</div>;

  if (history.length === 0) {
    return (
      <div className="empty-state">
        <div style={{ fontSize: '2.5rem' }}>📭</div>
        <p>No previous analyses yet.</p>
        <p>Run your first analysis to see it here.</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '1.5rem', letterSpacing: '-0.02em' }}>
        Application History
      </div>
      <div className="history-grid">
        {history.map((app, i) => {
          const score = app.ats_score || 0;
          const cls = getScoreClass(score);
          return (
            <div key={i} className="history-card">
              <div>
                <div className="history-title">{app.job_title || app.job_role || 'Unknown role'}</div>
                <div className="history-meta">{app.timestamp || ''}</div>
              </div>
              <div className={`history-score score-value ${cls}`}>{score}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
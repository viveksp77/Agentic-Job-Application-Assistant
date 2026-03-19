import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import { getHistory } from '../api/agent';

// ── helpers ────────────────────────────────────────────────────────────────

function formatDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function buildTrendData(applications) {
  return [...applications]
    .reverse()
    .map((app, i) => ({
      name: formatDate(app.timestamp),
      ats: parseFloat(app.ats_score) || 0,
      label: app.job_title || 'Unknown',
      index: i + 1,
    }));
}

function buildSkillsData(applications) {
  const counts = {};
  applications.forEach((app) => {
    const skills = (app.missing_skills || '')
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter((s) => s && s.length > 1 && !s.startsWith('skill'));
    skills.forEach((s) => {
      counts[s] = (counts[s] || 0) + 1;
    });
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([skill, count]) => ({ skill, count }));
}

// ── sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: '#1e1e2e',
      border: '1px solid #2a2a3d',
      borderRadius: 12,
      padding: '24px 28px',
      flex: 1,
      minWidth: 160,
    }}>
      <div style={{ color: '#888', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
        {label}
      </div>
      <div style={{ color: color || '#fff', fontSize: 36, fontWeight: 700, margin: '8px 0 4px' }}>
        {value}
      </div>
      {sub && <div style={{ color: '#666', fontSize: 12 }}>{sub}</div>}
    </div>
  );
}

const COLORS = ['#7c6af7', '#a78bfa', '#6366f1', '#818cf8', '#93c5fd', '#60a5fa', '#34d399', '#4ade80'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#1e1e2e', border: '1px solid #2a2a3d',
        borderRadius: 8, padding: '10px 14px', fontSize: 13,
      }}>
        <div style={{ color: '#aaa', marginBottom: 4 }}>{payload[0]?.payload?.label || label}</div>
        <div style={{ color: '#7c6af7', fontWeight: 600 }}>ATS: {payload[0]?.value}%</div>
      </div>
    );
  }
  return null;
};

// ── main component ─────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getHistory()
      .then((data) => {
        setApplications(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load analytics data.');
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div style={{ color: '#aaa', textAlign: 'center', marginTop: 80 }}>Loading analytics…</div>
  );

  if (error) return (
    <div style={{ color: '#f87171', textAlign: 'center', marginTop: 80 }}>{error}</div>
  );

  if (applications.length === 0) return (
    <div style={{ color: '#aaa', textAlign: 'center', marginTop: 80 }}>
      No data yet — run your first analysis to see analytics here.
    </div>
  );

  // ── derived stats ──────────────────────────────────────────────────────
  const scores = applications.map((a) => parseFloat(a.ats_score) || 0);
  const avgScore = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  const bestScore = Math.max(...scores).toFixed(1);
  const trendData = buildTrendData(applications);
  const skillsData = buildSkillsData(applications);

  // ── score colour ───────────────────────────────────────────────────────
  const scoreColor = (s) => s >= 70 ? '#34d399' : s >= 50 ? '#fbbf24' : '#f87171';

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 24px', color: '#fff' }}>

      {/* Header */}
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>📊 Analytics</h1>
      <p style={{ color: '#888', marginBottom: 36 }}>
        Insights across {applications.length} application{applications.length !== 1 ? 's' : ''}
      </p>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 40, flexWrap: 'wrap' }}>
        <StatCard
          label="Total Applications"
          value={applications.length}
          sub="analyses run"
        />
        <StatCard
          label="Average ATS Score"
          value={`${avgScore}%`}
          sub="across all jobs"
          color={scoreColor(parseFloat(avgScore))}
        />
        <StatCard
          label="Best ATS Score"
          value={`${bestScore}%`}
          sub="your strongest match"
          color={scoreColor(parseFloat(bestScore))}
        />
        <StatCard
          label="Skill Gaps Tracked"
          value={skillsData.length}
          sub="unique missing skills"
          color="#a78bfa"
        />
      </div>

      {/* ATS trend chart */}
      <div style={{
        background: '#1e1e2e', border: '1px solid #2a2a3d',
        borderRadius: 12, padding: '28px 24px', marginBottom: 32,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 24, color: '#ccc' }}>
          ATS Score Trend
        </h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={trendData} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3d" />
            <XAxis dataKey="name" tick={{ fill: '#666', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#666', fontSize: 12 }} unit="%" />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="ats"
              stroke="#7c6af7"
              strokeWidth={2.5}
              dot={{ fill: '#7c6af7', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Missing skills bar chart */}
      {skillsData.length > 0 && (
        <div style={{
          background: '#1e1e2e', border: '1px solid #2a2a3d',
          borderRadius: 12, padding: '28px 24px', marginBottom: 32,
        }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#ccc' }}>
            Top Missing Skills
          </h2>
          <p style={{ color: '#666', fontSize: 13, marginBottom: 20 }}>
            Skills that appeared most often as gaps across your applications
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={skillsData} margin={{ top: 4, right: 16, left: -16, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3d" />
              <XAxis
                dataKey="skill"
                tick={{ fill: '#888', fontSize: 11 }}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fill: '#666', fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #2a2a3d', borderRadius: 8 }}
                labelStyle={{ color: '#aaa' }}
                itemStyle={{ color: '#7c6af7' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {skillsData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent applications table */}
      <div style={{
        background: '#1e1e2e', border: '1px solid #2a2a3d',
        borderRadius: 12, padding: '28px 24px',
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, color: '#ccc' }}>
          Recent Applications
        </h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ color: '#666', textAlign: 'left' }}>
              <th style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3d' }}>Job Title</th>
              <th style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3d' }}>Date</th>
              <th style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3d' }}>ATS Score</th>
              <th style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3d' }}>Top Gap</th>
            </tr>
          </thead>
          <tbody>
            {applications.slice(0, 10).map((app, i) => {
              const score = parseFloat(app.ats_score) || 0;
              const topGap = (app.missing_skills || '').split(',')[0]?.trim() || '—';
              return (
                <tr key={i} style={{ borderBottom: '1px solid #1a1a2a' }}>
                  <td style={{ padding: '12px 12px', color: '#ddd' }}>
                    {app.job_title || 'Unknown'}
                  </td>
                  <td style={{ padding: '12px 12px', color: '#666' }}>
                    {new Date(app.timestamp).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '12px 12px' }}>
                    <span style={{
                      color: scoreColor(score),
                      fontWeight: 600,
                    }}>
                      {score.toFixed(1)}%
                    </span>
                  </td>
                  <td style={{ padding: '12px 12px', color: '#888' }}>{topGap}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
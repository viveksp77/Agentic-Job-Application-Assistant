import React, { useState } from 'react';

const TABS = [
  { id: 'gap',       label: '📊 Skill Gap' },
  { id: 'ats',       label: '🎯 ATS Score' },
  { id: 'resume',    label: '✏️ Resume' },
  { id: 'cover',     label: '📝 Cover Letter' },
  { id: 'interview', label: '❓ Interview Prep' },
  { id: 'roadmap',   label: '🎓 Skill Roadmap' },
  { id: 'summary',   label: '📈 Summary' },
];

function getScoreClass(score) {
  if (score >= 85) return 'excellent';
  if (score >= 70) return 'good';
  if (score >= 50) return 'fair';
  return 'poor';
}

function getBarColor(score) {
  if (score >= 85) return '#10b981';
  if (score >= 70) return '#34d399';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

function downloadText(text, filename) {
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function ResultTabs({ results }) {
  const [active, setActive] = useState('gap');

  const eval_ = results.evaluation || {};
  const gap = results.gap_analysis || {};
  const score = results.ats_score || 0;
  const scoreClass = getScoreClass(score);

  return (
    <div className="results-wrap">
      <div className="results-header">Results</div>

      <div className="tab-bar">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${active === t.id ? 'active' : ''}`}
            onClick={() => setActive(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">

        {/* ── Skill Gap ── */}
        {active === 'gap' && (
          <div>
            <div className="section-title">Matched skills</div>
            <div className="badge-group">
              {(eval_.strengths || []).length > 0
                ? (eval_.strengths || []).map(s => <span key={s} className="badge match">{s}</span>)
                : <span className="badge neutral">None detected</span>}
            </div>

            <div className="section-title" style={{ marginTop: '1.25rem' }}>Missing skills</div>
            <div className="badge-group">
              {(eval_.gaps || gap.missing_skills || []).length > 0
                ? (eval_.gaps || gap.missing_skills || []).map(s => <span key={s} className="badge missing">{s}</span>)
                : <span className="badge neutral">No gaps found</span>}
            </div>
          </div>
        )}

        {/* ── ATS Score ── */}
        {active === 'ats' && (
          <div>
            <div className="score-grid">
              <div className="score-card">
                <div className={`score-value ${scoreClass}`}>{score.toFixed(1)}%</div>
                <div className="score-label">ATS Score</div>
              </div>
              <div className="score-card">
                <div className={`score-value ${scoreClass}`}>{eval_.match_level || '—'}</div>
                <div className="score-label">Match level</div>
              </div>
              <div className="score-card">
                <div className="score-value" style={{ color: '#818cf8' }}>
                  {eval_.strengths_count || 0}/{( eval_.strengths_count || 0) + (eval_.skill_gaps_count || 0)}
                </div>
                <div className="score-label">Skills matched</div>
              </div>
            </div>

            <div className="ats-bar-bg">
              <div className="ats-bar-fill" style={{ width: `${score}%`, background: getBarColor(score) }} />
            </div>
          </div>
        )}

        {/* ── Resume Optimisation ── */}
        {active === 'resume' && (
          <div>
            <div className="section-title">Optimised resume bullets</div>
            {results.optimized_resume
              ? <>
                  <div className="content-block">{results.optimized_resume}</div>
                  <button className="download-btn" onClick={() => downloadText(results.optimized_resume, 'optimized_resume.txt')}>
                    ⬇ Download bullets
                  </button>
                </>
              : <div className="content-block" style={{ color: 'var(--muted)' }}>Optimisation not completed.</div>
            }
          </div>
        )}

        {/* ── Cover Letter ── */}
        {active === 'cover' && (
          <div>
            <div className="section-title">AI-generated cover letter</div>
            {results.cover_letter
              ? <>
                  <div className="content-block">{results.cover_letter}</div>
                  <button className="download-btn" onClick={() => downloadText(results.cover_letter, 'cover_letter.txt')}>
                    ⬇ Download cover letter
                  </button>
                </>
              : <div className="content-block" style={{ color: 'var(--muted)' }}>Generation not completed.</div>
            }
          </div>
        )}

        {/* ── Interview Questions ── */}
        {active === 'interview' && (
          <div>
            <div className="section-title">Targeted interview questions</div>
            <div className="question-list">
              {(results.interview_questions || []).length > 0
                ? results.interview_questions.map((q, i) => (
                    <div key={i} className="question-item">{q}</div>
                  ))
                : <div className="content-block" style={{ color: 'var(--muted)' }}>No questions generated.</div>
              }
            </div>
          </div>
        )}

        {/* ── Skill Roadmap ── */}
        {active === 'roadmap' && (
          <div>
            <div className="section-title">Learning roadmap</div>
            <div className="suggestion-list">
              {(results.skill_suggestions || []).filter(s => s.trim()).length > 0
                ? results.skill_suggestions.filter(s => s.trim()).map((s, i) => (
                    <div key={i} className="suggestion-item">
                      <span className="suggestion-dot">›</span>
                      <span>{s}</span>
                    </div>
                  ))
                : <div className="content-block" style={{ color: 'var(--muted)' }}>No suggestions generated.</div>
              }
            </div>
          </div>
        )}

        {/* ── Summary ── */}
        {active === 'summary' && (
          <div>
            <div className={`recommendation-banner ${scoreClass}`}>
              {eval_.recommendation || 'Analysis complete.'}
            </div>

            <div className="section-title">Session stats</div>
            <div className="stats-row">
              <span className="stat-pill">Resume skills: {(results.resume_skills || []).length}</span>
              <span className="stat-pill">Job skills: {(results.job_skills || []).length}</span>
              <span className="stat-pill">ATS: {score.toFixed(1)}%</span>
              <span className="stat-pill">Gaps: {(eval_.skill_gaps_count || 0)}</span>
            </div>

            <div className="section-title" style={{ marginTop: '1.25rem' }}>All resume skills</div>
            <div className="badge-group">
              {(results.resume_skills || []).map(s => <span key={s} className="badge neutral">{s}</span>)}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
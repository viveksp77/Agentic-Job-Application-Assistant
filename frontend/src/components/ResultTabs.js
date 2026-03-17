import React, { useState, useEffect, useRef } from 'react';
import { streamCoverLetter, streamInterviewQuestions } from '../api/agent';

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

// ---------------------------------------------------------------------------
// Streaming text component — shows a blinking cursor while streaming
// ---------------------------------------------------------------------------
function StreamingText({ text, isStreaming }) {
  return (
    <div className="content-block" style={{ whiteSpace: 'pre-wrap', minHeight: 80 }}>
      {text}
      {isStreaming && (
        <span style={{
          display: 'inline-block',
          width: 2,
          height: '1em',
          background: 'var(--accent)',
          marginLeft: 2,
          verticalAlign: 'text-bottom',
          animation: 'blink 0.7s step-end infinite',
        }} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ResultTabs component
// ---------------------------------------------------------------------------
export default function ResultTabs({ results }) {
  const [active, setActive] = useState('gap');

  // Cover letter streaming state
  const [coverText, setCoverText]         = useState(results.cover_letter || '');
  const [coverStreaming, setCoverStreaming] = useState(false);
  const [coverStarted, setCoverStarted]   = useState(!!results.cover_letter);
  const cancelCoverRef = useRef(null);

  // Interview questions streaming state
  const [interviewText, setInterviewText]         = useState('');
  const [interviewStreaming, setInterviewStreaming] = useState(false);
  const [interviewStarted, setInterviewStarted]   = useState(false);
  const [parsedQuestions, setParsedQuestions]     = useState(results.interview_questions || []);
  const cancelInterviewRef = useRef(null);

  const eval_  = results.evaluation || {};
  const gap    = results.gap_analysis || {};
  const score  = results.ats_score || 0;
  const scoreClass = getScoreClass(score);

  // Build streaming payload from results
  const streamPayload = {
    job_title:      results.jd_analysis?.job_title || 'the role',
    job_desc:       results.jd_analysis?.full_analysis || '',
    resume_summary: results.resume_text?.slice(0, 800) || '',
    strengths:      (results.resume_skills || []).slice(0, 6).join(', '),
    missing_skills: results.missing_skills || [],
    resume_id:      results.resume_id || null,
  };

  // ---------------------------------------------------------------------------
  // Streaming handlers
  // ---------------------------------------------------------------------------

  const startCoverStream = () => {
    setCoverText('');
    setCoverStreaming(true);
    setCoverStarted(true);

    cancelCoverRef.current = streamCoverLetter(
      streamPayload,
      (token) => setCoverText(prev => prev + token),
      () => setCoverStreaming(false),
      (err) => { setCoverStreaming(false); setCoverText(`Error: ${err}`); }
    );
  };

  const startInterviewStream = () => {
    setInterviewText('');
    setInterviewStreaming(true);
    setInterviewStarted(true);
    setParsedQuestions([]);

    const payload = {
      job_desc:      results.jd_analysis?.full_analysis || '',
      resume_skills: results.resume_skills || [],
      resume_id:     results.resume_id || null,
    };

    cancelInterviewRef.current = streamInterviewQuestions(
      payload,
      (token) => setInterviewText(prev => prev + token),
      () => {
        setInterviewStreaming(false);
        // Parse numbered questions from streamed text
        setInterviewText(prev => {
          const lines = prev.split('\n');
          const questions = lines
            .filter(l => /^\d+[\.\)]/.test(l.trim()))
            .map(l => l.replace(/^\d+[\.\)]\s*/, '').trim())
            .filter(Boolean);
          if (questions.length > 0) setParsedQuestions(questions);
          return prev;
        });
      },
      (err) => { setInterviewStreaming(false); setInterviewText(`Error: ${err}`); }
    );
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (cancelCoverRef.current) cancelCoverRef.current();
      if (cancelInterviewRef.current) cancelInterviewRef.current();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="results-wrap">
      {/* Cursor blink animation */}
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>

      <div className="results-header">Results</div>

      <div className="tab-bar">
        {TABS.map(t => (
          <button key={t.id} className={`tab-btn ${active === t.id ? 'active' : ''}`}
            onClick={() => setActive(t.id)}>
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
                  {eval_.strengths_count || 0}/{(eval_.strengths_count || 0) + (eval_.skill_gaps_count || 0)}
                </div>
                <div className="score-label">Skills matched</div>
              </div>
            </div>
            <div className="ats-bar-bg">
              <div className="ats-bar-fill" style={{ width: `${score}%`, background: getBarColor(score) }} />
            </div>
          </div>
        )}

        {/* ── Resume ── */}
        {active === 'resume' && (
          <div>
            <div className="section-title">Optimised resume bullets</div>
            {results.optimized_resume
              ? <>
                  <div className="content-block">{results.optimized_resume}</div>
                  <button className="download-btn"
                    onClick={() => downloadText(results.optimized_resume, 'optimized_resume.txt')}>
                    ⬇ Download bullets
                  </button>
                </>
              : <div className="content-block" style={{ color: 'var(--muted)' }}>Not completed.</div>
            }
          </div>
        )}

        {/* ── Cover Letter (streaming) ── */}
        {active === 'cover' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div className="section-title" style={{ margin: 0 }}>AI-generated cover letter</div>
              <button className="download-btn" style={{ marginTop: 0 }}
                onClick={startCoverStream} disabled={coverStreaming}>
                {coverStreaming ? '⏳ Generating...' : coverStarted ? '↺ Regenerate' : '▶ Generate (live)'}
              </button>
            </div>

            {coverStarted
              ? <>
                  <StreamingText text={coverText} isStreaming={coverStreaming} />
                  {!coverStreaming && coverText && (
                    <button className="download-btn"
                      onClick={() => downloadText(coverText, 'cover_letter.txt')}>
                      ⬇ Download cover letter
                    </button>
                  )}
                </>
              : <div className="content-block" style={{ color: 'var(--muted)' }}>
                  Click "Generate (live)" to stream your cover letter in real time.
                </div>
            }
          </div>
        )}

        {/* ── Interview Questions (streaming) ── */}
        {active === 'interview' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div className="section-title" style={{ margin: 0 }}>Targeted interview questions</div>
              <button className="download-btn" style={{ marginTop: 0 }}
                onClick={startInterviewStream} disabled={interviewStreaming}>
                {interviewStreaming ? '⏳ Generating...' : interviewStarted ? '↺ Regenerate' : '▶ Generate (live)'}
              </button>
            </div>

            {interviewStarted ? (
              interviewStreaming
                ? <StreamingText text={interviewText} isStreaming={true} />
                : parsedQuestions.length > 0
                  ? <div className="question-list">
                      {parsedQuestions.map((q, i) => (
                        <div key={i} className="question-item">{q}</div>
                      ))}
                    </div>
                  : <div className="content-block">{interviewText}</div>
            ) : (
              <div className="content-block" style={{ color: 'var(--muted)' }}>
                {(results.interview_questions || []).length > 0
                  ? <div className="question-list">
                      {results.interview_questions.map((q, i) => (
                        <div key={i} className="question-item">{q}</div>
                      ))}
                    </div>
                  : 'Click "Generate (live)" to stream interview questions in real time.'
                }
              </div>
            )}
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
              <span className="stat-pill">Gaps: {eval_.skill_gaps_count || 0}</span>
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
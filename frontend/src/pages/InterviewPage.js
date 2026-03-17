import React, { useState } from 'react';
import { getInterviewQuestion, evaluateAnswer } from '../api/agent';

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'];
const TOTAL_QUESTIONS = 5;

function ScoreBar({ label, value }) {
  const color = value >= 8 ? '#10b981' : value >= 6 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ marginBottom: '0.6rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
        <span style={{ fontSize: '0.85rem', fontFamily: 'DM Mono, monospace', color }}>{value}/10</span>
      </div>
      <div style={{ height: 4, background: 'var(--border2)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${value * 10}%`, background: color, borderRadius: 99, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

function FinalReport({ scores, jobRole, onRestart }) {
  const avg = (key) => Math.round(scores.reduce((s, q) => s + (q.scores?.[key] || 0), 0) / scores.length);
  const overall = Math.round((avg('clarity') + avg('relevance') + avg('depth')) / 3);
  const overallColor = overall >= 8 ? '#10b981' : overall >= 6 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
        <div style={{ fontSize: '3.5rem', fontWeight: 600, fontFamily: 'DM Mono, monospace', color: overallColor }}>
          {overall}/10
        </div>
        <div style={{ color: 'var(--muted)', marginTop: 4 }}>Overall performance</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
        {[
          { label: 'Clarity', key: 'clarity' },
          { label: 'Relevance', key: 'relevance' },
          { label: 'Depth', key: 'depth' },
        ].map(({ label, key }) => (
          <div key={key} style={{ background: 'var(--bg3)', border: '1px solid var(--border2)', borderRadius: 8, padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.6rem', fontWeight: 600, fontFamily: 'DM Mono, monospace', color: 'var(--accent2)' }}>{avg(key)}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>

      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.75rem' }}>
          Question breakdown
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {scores.map((q, i) => (
            <div key={i} style={{ background: 'var(--bg3)', border: '1px solid var(--border2)', borderRadius: 8, padding: '1rem' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>Q{i + 1}: {q.question?.slice(0, 80)}...</div>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {['clarity', 'relevance', 'depth'].map(k => (
                  <span key={k} style={{ fontSize: '0.8rem', fontFamily: 'DM Mono, monospace', color: 'var(--text)' }}>
                    {k}: <span style={{ color: 'var(--accent2)' }}>{q.scores?.[k] ?? '—'}</span>
                  </span>
                ))}
              </div>
              {q.scores?.strength && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.82rem', color: '#34d399' }}>+ {q.scores.strength}</div>
              )}
              {q.scores?.improvement && (
                <div style={{ fontSize: '0.82rem', color: '#f59e0b' }}>↑ {q.scores.improvement}</div>
              )}
            </div>
          ))}
        </div>
      </div>

      <button className="submit-btn" onClick={onRestart}>
        ↺ Start New Interview
      </button>
    </div>
  );
}

export default function InterviewPage() {
  const [stage, setStage] = useState('setup');   // setup | interview | report
  const [jobRole, setJobRole] = useState('');
  const [difficulty, setDifficulty] = useState('Medium');
  const [conversation, setConversation] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [userAnswer, setUserAnswer] = useState('');
  const [questionNumber, setQuestionNumber] = useState(1);
  const [evaluation, setEvaluation] = useState(null);
  const [allScores, setAllScores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const startInterview = async () => {
    if (!jobRole.trim()) { setError('Please enter a job role.'); return; }
    setError('');
    setLoading(true);
    try {
      const data = await getInterviewQuestion(jobRole, difficulty, [], 1);
      setCurrentQuestion(data.question);
      setConversation([{ role: 'assistant', content: data.question }]);
      setStage('interview');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!userAnswer.trim()) return;
    setLoading(true);
    setEvaluation(null);

    const updatedConv = [
      ...conversation,
      { role: 'user', content: userAnswer },
    ];

    try {
      const eval_ = await evaluateAnswer(jobRole, difficulty, conversation, userAnswer);
      setEvaluation(eval_);

      const newScore = {
        question: currentQuestion,
        answer: userAnswer,
        scores: eval_,
      };
      const newAllScores = [...allScores, newScore];
      setAllScores(newAllScores);

      if (questionNumber >= TOTAL_QUESTIONS) {
        setStage('report');
        return;
      }

      // Load next question
      const nextNum = questionNumber + 1;
      const nextData = await getInterviewQuestion(jobRole, difficulty, updatedConv, nextNum);

      const newConv = [
        ...updatedConv,
        { role: 'assistant', content: nextData.question },
      ];
      setConversation(newConv);
      setCurrentQuestion(nextData.question);
      setQuestionNumber(nextNum);
      setUserAnswer('');
      setEvaluation(null);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const restart = () => {
    setStage('setup');
    setJobRole('');
    setDifficulty('Medium');
    setConversation([]);
    setCurrentQuestion('');
    setUserAnswer('');
    setQuestionNumber(1);
    setEvaluation(null);
    setAllScores([]);
    setError('');
  };

  // ── Setup screen ──
  if (stage === 'setup') {
    return (
      <div style={{ maxWidth: 560, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div className="hero" style={{ paddingBottom: 0 }}>
          <h1>Mock <span>Interview</span> Simulator</h1>
          <p>5 AI-generated questions, scored in real time.</p>
        </div>

        <div className="form-card">
          <span className="form-label">Job Role</span>
          <input
            style={{
              width: '100%', padding: '0.75rem', background: 'var(--bg3)',
              border: '1px solid var(--border2)', borderRadius: 8,
              color: 'var(--text)', fontFamily: 'inherit', fontSize: '0.95rem',
              outline: 'none',
            }}
            placeholder="e.g. Software Engineer, Data Scientist, ML Engineer"
            value={jobRole}
            onChange={e => setJobRole(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && startInterview()}
          />
        </div>

        <div className="form-card">
          <span className="form-label">Difficulty</span>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            {DIFFICULTIES.map(d => (
              <button
                key={d}
                onClick={() => setDifficulty(d)}
                style={{
                  flex: 1, padding: '0.6rem',
                  background: difficulty === d ? 'var(--accent)' : 'var(--bg3)',
                  border: `1px solid ${difficulty === d ? 'var(--accent)' : 'var(--border2)'}`,
                  borderRadius: 8, color: 'var(--text)',
                  fontFamily: 'inherit', fontSize: '0.9rem',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button className="submit-btn" onClick={startInterview} disabled={loading}>
          {loading ? 'Loading question...' : '▶ Start Interview'}
        </button>
      </div>
    );
  }

  // ── Report screen ──
  if (stage === 'report') {
    return (
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        <div style={{ fontSize: '1.3rem', fontWeight: 600, letterSpacing: '-0.02em', marginBottom: '1.5rem' }}>
          Interview Complete — {jobRole}
        </div>
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12, padding: '1.5rem' }}>
          <FinalReport scores={allScores} jobRole={jobRole} onRestart={restart} />
        </div>
      </div>
    );
  }

  // ── Interview screen ──
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{jobRole}</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>{difficulty} · Question {questionNumber} of {TOTAL_QUESTIONS}</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {Array.from({ length: TOTAL_QUESTIONS }).map((_, i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: '50%',
              background: i < questionNumber - 1 ? '#10b981' : i === questionNumber - 1 ? 'var(--accent)' : 'var(--border2)',
              transition: 'background 0.3s',
            }} />
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, background: 'var(--border2)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${((questionNumber - 1) / TOTAL_QUESTIONS) * 100}%`, background: 'var(--accent)', transition: 'width 0.4s ease' }} />
      </div>

      {/* Question */}
      <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12, padding: '1.5rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.75rem' }}>
          Question {questionNumber}
        </div>
        <div style={{ fontSize: '1.05rem', lineHeight: 1.6, color: 'var(--text)' }}>
          {currentQuestion}
        </div>
      </div>

      {/* Evaluation feedback (shown after submitting) */}
      {evaluation && (
        <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12, padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Your score</div>
          <ScoreBar label="Clarity" value={evaluation.clarity} />
          <ScoreBar label="Relevance" value={evaluation.relevance} />
          <ScoreBar label="Depth" value={evaluation.depth} />
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem', fontSize: '0.88rem', color: 'var(--text)', lineHeight: 1.6 }}>
            {evaluation.feedback}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.82rem', color: '#34d399' }}>+ {evaluation.strength}</span>
            <span style={{ fontSize: '0.82rem', color: '#f59e0b' }}>↑ {evaluation.improvement}</span>
          </div>
        </div>
      )}

      {/* Answer input */}
      {!evaluation && (
        <>
          <textarea
            className="textarea"
            placeholder="Type your answer here..."
            value={userAnswer}
            onChange={e => setUserAnswer(e.target.value)}
            style={{ minHeight: 140 }}
            disabled={loading}
          />
          {error && <div className="error-msg">{error}</div>}
          <button className="submit-btn" onClick={submitAnswer} disabled={loading || !userAnswer.trim()}>
            {loading ? 'Evaluating...' : questionNumber === TOTAL_QUESTIONS ? 'Submit Final Answer →' : 'Submit Answer →'}
          </button>
        </>
      )}

      {/* Next question button shown after evaluation */}
      {evaluation && questionNumber < TOTAL_QUESTIONS && (
        <button className="submit-btn" onClick={() => setEvaluation(null)} disabled={loading}>
          {loading ? 'Loading next question...' : `Next Question (${questionNumber + 1}/${TOTAL_QUESTIONS}) →`}
        </button>
      )}
    </div>
  );
}